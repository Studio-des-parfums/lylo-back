"""Service de génération de formules de parfum.

Architecture :
  1. Récupère les ingrédients depuis l'API dashboard (filtrés par box_set/langue)
  2. Envoie au LLM les réponses + ingrédients disponibles
  3. Le LLM sélectionne les notes, déduit le profil et le type de formule
  4. Calcul des ml selon le tableau des formules (inchangé)
"""

import asyncio
import json
import time
from decimal import Decimal, ROUND_DOWN

import httpx
from openai import AsyncOpenAI

from app.config import get_settings
from app.services import moodboard_service, session_store

# ── Configuration des types de formules ──────────────────────────────
_FORMULA_TYPE_CONFIGS: dict[str, dict] = {
    "frais": {
        "note_counts": {"top": 3, "heart": 3, "base": 2},
        "sizes": {
            10: {"top_ml": 2, "heart_ml": 2, "base_ml": 4, "booster_ml": 2},
            30: {"top_ml": 6, "heart_ml": 6, "base_ml": 12, "booster_ml": 6},
            50: {"top_ml": 10, "heart_ml": 10, "base_ml": 20, "booster_ml": 10},
        },
    },
    "mix": {
        "note_counts": {"top": 2, "heart": 3, "base": 2},
        "sizes": {
            10: {"top_ml": 2, "heart_ml": 2, "base_ml": 4, "booster_ml": 2},
            30: {"top_ml": 6, "heart_ml": 6, "base_ml": 12, "booster_ml": 6},
            50: {"top_ml": 10, "heart_ml": 10, "base_ml": 20, "booster_ml": 10},
        },
    },
    "puissant": {
        "note_counts": {"top": 2, "heart": 2, "base": 3},
        "sizes": {
            10: {"top_ml": 2, "heart_ml": 2, "base_ml": 4, "booster_ml": 2},
            30: {"top_ml": 4, "heart_ml": 8, "base_ml": 12, "booster_ml": 6},
            50: {"top_ml": 8, "heart_ml": 12, "base_ml": 20, "booster_ml": 10},
        },
    },
}

# Mots-clés utilisés pour choisir le booster le plus cohérent avec la formule.
# L'API dashboard ne fournit ni description ni mots-clés pour les ingrédients de
# type "booster" : ce mapping (par nom de booster) comble ce manque côté code.
# Fallback si un booster renvoyé par l'API n'a pas d'entrée ici : liste de mots-clés vide (score 0).

# Mots-clés utilisés pour juger si une note (nom + description) est plutôt légère ou
# plutôt intense, INDÉPENDAMMENT du champ `intensity` de l'API dashboard — celui-ci
# s'est avéré peu fiable en pratique (souvent absent, ou "legere" même pour des notes
# épicées/boisées). Sert de filet de sécurité en code pour empêcher le LLM de glisser
# une note fraîche dans une formule "puissant" (ou inversement), ce qu'une simple
# consigne en langage naturel ne suffit pas toujours à garantir.
_LIGHT_KEYWORDS = [
    "frais", "fraîche", "fraicheur", "légère", "légèreté", "brise", "aquatique",
    "marine", "ozonic", "ozonique", "aqueuse", "pétillante", "verte", "vert",
    "agrume", "citron", "bergamote", "pamplemousse", "linge", "propre", "coton",
    "aldéhyd", "poudré", "poudree",
]
_INTENSE_KEYWORDS = [
    "boisé", "boisee", "bois", "ambre", "ambré", "ambree", "cuir", "cuirée", "cuiree",
    "épice", "epice", "chaud", "chaude", "oriental", "tabac", "musc profond",
    "animale", "résine", "resine", "oud", "vanille", "patchouli", "terreux",
    "terreuse", "sensuel", "capiteux", "capiteuse", "encens",
]


def _note_intensity_score(name: str, description: str) -> int:
    """Score grossier : positif = plutôt intense, négatif = plutôt léger, 0 = neutre."""
    text = f"{name} {description}".lower()
    score = sum(1 for kw in _INTENSE_KEYWORDS if kw in text)
    score -= sum(1 for kw in _LIGHT_KEYWORDS if kw in text)
    return score


_BOOSTER_KEYWORDS: dict[str, list[str]] = {
    "Musc Blanc": ["musc", "propre", "frais", "clean", "musk", "coton",
                   "savon", "linge", "poudré", "aldéhyde", "blanc",
                   "minéral", "ozonic", "aquatique", "agrume",
                   "bergamote", "citron", "pamplemousse"],
    "Musc Floral": ["fleur", "rose", "jasmin", "muguet", "floral", "flower",
                    "pétale", "bouquet", "pivoine", "iris", "ylang",
                    "néroli", "magnolia", "tubéreuse", "gardénia"],
    "Accord Musc": ["ambre", "vanille", "oriental", "chaud", "doux", "warm",
                    "amber", "gourmand", "caramel", "miel", "tonka",
                    "baume", "résine", "encens", "oud", "boisé", "musc profond",
                    "sensuel"],
}


# ── Chargement des ingrédients depuis l'API dashboard ──────────────────
#
# Le catalogue d'ingrédients change rarement (c'est un service tiers, le
# dashboard SDP) mais est ré-interrogé à chaque étape de personnalisation
# (changement de type, remplacement de note, etc.) pendant une même session
# vocale. On met donc en cache la réponse brute de l'API en mémoire process,
# le temps d'un court TTL, pour éviter de repayer la latence réseau à chaque
# tour de conversation.

_CACHE_TTL_SECONDS = 60.0
_ingredients_api_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}


async def _fetch_ingredients_raw(params: dict) -> list[dict]:
    """Appelle GET /api/ingredients avec les `params` donnés, avec cache court en mémoire.

    La clé de cache est (box_set, language) ou (type, language) selon les params
    passés — cohérent avec le fait que `_load_ingredients_from_db` et
    `_load_boosters_from_db` tapent le même endpoint avec des filtres différents.
    """
    settings = get_settings()
    cache_key = (params.get("box_set") or params.get("type") or "", params.get("language", ""))

    now = time.monotonic()
    cached = _ingredients_api_cache.get(cache_key)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{settings.ingredients_api_url}/api/ingredients", params=params)
        response.raise_for_status()
        raw = response.json()

    _ingredients_api_cache[cache_key] = (now, raw)
    return raw


async def _load_ingredients_from_db(language: str, category: str | None = None) -> list[dict]:
    """Récupère les ingrédients depuis l'API externe du dashboard SDP.

    Note : le paramètre `category` n'existe pas côté API dashboard (qui filtre
    par `box_set`) ; il est conservé pour compatibilité de signature mais ignoré.
    """
    settings = get_settings()
    params = {
        "box_set": settings.ingredients_box_set,
        "active_only": "true",
        "language": language,
    }
    raw_ingredients = await _fetch_ingredients_raw(params)

    ingredients = []
    for i in raw_ingredients:
        translations = i.get("translations") or {}
        name = translations.get(language) or translations.get("fr") or translations.get("en") or ""
        if not name:
            continue
        ingredients.append({
            "id": i.get("id"),
            "name": name,
            "type": i.get("type"),
            "description": i.get("description") or "",
            "intensity": i.get("intensity") or "",
            "allergens": i.get("allergens"),
        })
    return ingredients


async def _load_boosters_from_db(language: str) -> list[dict]:
    """Récupère les ingrédients de type "booster" depuis l'API dashboard.

    Les boosters ne sont pas rattachés à un box_set : on ne filtre donc pas par
    `box_set` (contrairement à `_load_ingredients_from_db`), sous peine de ne
    jamais en recevoir.
    """
    params = {
        "type": "booster",
        "active_only": "true",
        "language": language,
    }
    raw_boosters = await _fetch_ingredients_raw(params)

    boosters = []
    for b in raw_boosters:
        if b.get("type") != "booster":
            continue
        translations = b.get("translations") or {}
        name = translations.get(language) or translations.get("fr") or translations.get("en") or ""
        if not name:
            continue
        boosters.append({"id": b.get("id"), "name": name})
    return boosters


# Fallback ultime : si l'API ne renvoie aucun booster actif, on ne doit
# jamais laisser une formule sans booster.
_FALLBACK_BOOSTER = {"id": None, "name": "Musc Blanc"}


async def _load_boosters_with_fallback(language: str) -> list[dict]:
    try:
        boosters = await _load_boosters_from_db(language)
    except (httpx.HTTPError, ValueError):
        boosters = []
    return boosters or [_FALLBACK_BOOSTER]


# ── Appel LLM ────────────────────────────────────────────────────────

def _format_ingredients_prompt(ingredients: list[dict], excluded_names: set[str]) -> tuple[str, str, str]:
    """Construit les 3 blocs de texte (top/heart/base) listant les ingrédients disponibles."""
    available = [i for i in ingredients if i["name"] not in excluded_names]

    def format_ingredients(note_type: str) -> str:
        items = [i for i in available if i["type"] == note_type]
        if not items:
            return "Aucune note disponible"
        lines = []
        for i in items:
            allergen_info = ""
            if i["allergens"]:
                allergen_info = f" [allergènes connus: {', '.join(i['allergens'])}]"
            desc = f" — {i['description']}" if i['description'] else ""
            intensity = f" (intensité: {i['intensity']})" if i['intensity'] else ""
            lines.append(f"- {i['name']}{desc}{intensity}{allergen_info}")
        return "\n".join(lines)

    return format_ingredients("top"), format_ingredients("heart"), format_ingredients("base")


def _build_formula_system_user_prompts(
    answers: dict,
    ingredients: list[dict],
    user_allergens: list[str] | None,
    excluded_names: set[str],
    excluded_profiles: set[str],
    language: str,
    force_type: str | None,
    formula_count: int,
) -> tuple[str, str]:
    top_block, heart_block, base_block = _format_ingredients_prompt(ingredients, excluded_names)

    # Résumé des réponses au questionnaire
    answers_summary = []
    for qid, data in answers.items():
        if isinstance(data, str):
            data = json.loads(data)
        q = data.get("question", f"Question {qid}")
        top = ", ".join(data.get("top_2", []))
        bottom = ", ".join(data.get("bottom_2", []))
        answers_summary.append(f"- {q}\n  Préférées: {top}\n  Moins appréciées: {bottom}")

    allergen_instruction = ""
    if user_allergens:
        allergen_instruction = f"""
Le client a déclaré les allergies suivantes : {', '.join(user_allergens)}.
- Si une note a des allergènes listés qui correspondent, EXCLUE-la obligatoirement.
- Si une note n'a pas d'allergènes listés, utilise ton jugement sur sa composition habituelle pour évaluer le risque.
"""
    else:
        allergen_instruction = "Le client n'a pas déclaré d'allergies."

    excluded_profiles_instruction = ""
    if excluded_profiles:
        excluded_profiles_instruction = f"Les profils suivants sont déjà utilisés dans une autre formule, choisis un profil différent : {', '.join(excluded_profiles)}."

    _INTENSITY_GUIDANCE = {
        "frais": """Le client veut un parfum LÉGER (frais, discret, peu tenace) — AUCUNE note boisée, ambrée, épicée chaude, orientale, cuir ou musquée profonde n'est autorisée, même en note de fond.
- Sélectionne exactement 3 notes de tête, 3 de cœur, 2 de fond.
- N'utilise QUE des notes dont le nom ou la description évoque : agrumes, notes vertes/aquatiques, fleurs blanches ou fruitées légères, thé, notes marines/ozoniques. Le champ d'intensité entre parenthèses, quand il est présent, doit être "légère" ou "moyenne" — jamais "forte".
- Même les notes de fond doivent rester légères (musc blanc/propre, bois clair, notes poudrées douces) : pas de patchouli, oud, ambre, cuir, tabac, épices chaudes.
- La formule doit rester subtile et peu capiteuse : sillage discret, jamais de puissance.""",
        "mix": """Le client veut un parfum ÉQUILIBRÉ (ni trop léger, ni trop capiteux, un juste milieu).
- Sélectionne exactement 2 notes de tête, 3 de cœur, 2 de fond.
- Mélange des notes légères/fraîches avec 1 ou 2 notes plus marquées (boisées, épicées, ambrées) pour donner du caractère sans être écrasant.
- Vise un équilibre harmonieux entre fraîcheur et profondeur, perceptible dans le choix réel des notes.""",
        "puissant": """Le client veut un parfum INTENSE (capiteux, marquant, tenace) — AUCUNE note fraîche, aquatique, ozonique, agrume dominant ou "brise/fraîcheur" n'est autorisée, même en note de tête.
- Sélectionne exactement 2 notes de tête, 2 de cœur, 3 de fond.
- N'utilise QUE des notes dont le nom ou la description évoque : bois, ambre, épices chaudes, cuir, tabac, oriental, résine, musc profond, oud, vanille, patchouli. Le champ d'intensité entre parenthèses, quand il est présent, doit être "forte" — jamais "légère".
- Même la note de tête doit rester marquée (épices chaudes, agrumes puissants type pamplemousse noir, jamais une note "fraîche"/"brise"/aldéhydée légère).
- La formule doit avoir un sillage puissant et une forte tenue du début à la fin.""",
    }

    force_type_instruction = ""
    if force_type and force_type in _FORMULA_TYPE_CONFIGS:
        force_type_instruction = f'Le type de formule est imposé : "{force_type}".\n{_INTENSITY_GUIDANCE[force_type]}'
    else:
        force_type_instruction = f"""Déduis le type de formule le plus adapté au profil, puis applique STRICTEMENT sa consigne d'intensité :
- "frais" : {_INTENSITY_GUIDANCE["frais"]}
- "mix" : {_INTENSITY_GUIDANCE["mix"]}
- "puissant" : {_INTENSITY_GUIDANCE["puissant"]}"""

    note_entry_schema = '{"name": "nom exact de la note", "alternatives": ["alternative1", "alternative2"]}'
    formula_schema = """{
  "profile": "nom du profil olfactif (ex: Visionary, Creator, Icon, Disruptor, Trailblazer, Innovator, Strategist, Influencer, Cosy)",
  "profile_description": "description courte et poétique du profil en %s (2-3 phrases), qui doit expliquer brièvement en quoi les notes choisies donnent au parfum son caractère léger/équilibré/intense (selon le type de formule) sans être technique",
  "formula_type": "frais | mix | puissant",
  "top_notes": [%s, %s],
  "heart_notes": [%s, %s, %s],
  "base_notes": [%s, %s]
}""" % (
        "français" if language == "fr" else "anglais",
        note_entry_schema, note_entry_schema,
        note_entry_schema, note_entry_schema, note_entry_schema,
        note_entry_schema, note_entry_schema,
    )

    if formula_count == 1:
        response_format_instruction = f"""Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, dans ce format exact :
{formula_schema}"""
        formulas_instruction = "Sélectionne les notes les plus cohérentes avec les préférences du client et crée une formule harmonieuse."
    else:
        response_format_instruction = f"""Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, dans ce format exact :
{{
  "formulas": [{formula_schema}, {formula_schema}]
}}"""
        formulas_instruction = (
            f"Crée {formula_count} formules DISTINCTES et cohérentes avec les préférences du client. "
            "Chaque formule doit avoir un profil olfactif différent et ne pas réutiliser exactement les mêmes notes qu'une autre formule de la liste."
        )

    system_prompt = f"""Tu es un expert en parfumerie. Tu dois créer {"une formule de parfum personnalisée" if formula_count == 1 else f"{formula_count} formules de parfum personnalisées"} pour un client en analysant ses réponses à un questionnaire olfactif.

{response_format_instruction}

Les noms des notes doivent correspondre EXACTEMENT aux noms disponibles dans la liste fournie.

Pour CHAQUE note (tête, cœur, fond), fournis aussi 2 alternatives : des notes du MÊME type (tête/cœur/fond) et de la liste disponible, olfactivement cohérentes avec le profil et pouvant remplacer la note principale si le client ne l'aime pas. Les alternatives d'une note ne doivent pas être déjà utilisées ailleurs dans la même formule.

La préférence d'intensité du client (frais/mix/puissant, précisée plus bas) doit vraiment guider le CHOIX des notes elles-mêmes (pas seulement leur nombre) : le champ d'intensité entre parenthèses, quand présent, est indicatif, mais si une note n'a pas d'intensité indiquée, juge par son nom et sa description si elle est cohérente avec le registre demandé (léger/équilibré/intense) — en cas de doute, choisis une autre note plutôt qu'une note ambiguë. Ne sélectionne JAMAIS une note dont le nom ou la description contredit clairement le registre demandé (ex : une note "fraîche"/"brise"/"légère" dans une formule "puissant", ou une note "boisée profonde"/"cuir"/"ambrée" dans une formule "frais").

Dans "profile_description", explique en 2-3 phrases courtes et non techniques pourquoi CES notes précises (celles réellement choisies dans top_notes/heart_notes/base_notes) donnent au parfum son caractère léger/équilibré/intense. Ne mentionne QUE des familles olfactives (boisé, ambré, musqué, floral, agrumes...) effectivement présentes parmi les notes choisies — n'invente jamais une famille absente de la sélection. Reste concis, pas de liste, pas de jargon de parfumeur."""

    user_prompt = f"""Voici les réponses du client au questionnaire :
{chr(10).join(answers_summary)}

Notes de tête disponibles :
{top_block}

Notes de cœur disponibles :
{heart_block}

Notes de fond disponibles :
{base_block}

{allergen_instruction}
{excluded_profiles_instruction}
{force_type_instruction}

{formulas_instruction}"""

    return system_prompt, user_prompt


async def _ask_llm_for_formula(
    answers: dict,
    ingredients: list[dict],
    user_allergens: list[str] | None,
    excluded_names: set[str],
    excluded_profiles: set[str],
    language: str,
    force_type: str | None,
) -> dict:
    """Demande au LLM de sélectionner les notes et de déduire le profil pour UNE formule."""
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    system_prompt, user_prompt = _build_formula_system_user_prompts(
        answers, ingredients, user_allergens, excluded_names, excluded_profiles, language, force_type,
        formula_count=1,
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    return json.loads(response.choices[0].message.content)


async def _ask_llm_for_formulas(
    answers: dict,
    ingredients: list[dict],
    user_allergens: list[str] | None,
    language: str,
    force_type: str | None,
    formula_count: int = 2,
) -> list[dict]:
    """Demande au LLM de générer PLUSIEURS formules en un seul appel (au lieu d'un appel séquentiel par formule).

    Le LLM voit toutes les formules à produire simultanément, ce qui garantit nativement
    leur diversité (profils/notes différents) sans avoir besoin d'un aller-retour réseau
    par formule ni de lui repasser en second tour les choix déjà faits.
    """
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    system_prompt, user_prompt = _build_formula_system_user_prompts(
        answers, ingredients, user_allergens, set(), set(), language, force_type,
        formula_count=formula_count,
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    parsed = json.loads(response.choices[0].message.content)
    results = parsed.get("formulas", [])
    if not results:
        # Filet de sécurité si le LLM n'a pas respecté le schéma { "formulas": [...] }
        results = [parsed]
    return results[:formula_count]


# ── Calcul des quantités en ml ────────────────────────────────────────

def _select_booster(note_names: list[str], descriptions: list[str], boosters: list[dict]) -> dict:
    """Choisit le booster le plus cohérent avec les notes de la formule.

    `boosters` doit toujours contenir au moins un élément (garanti par l'appelant) :
    on retourne systématiquement un booster, même sans aucun mot-clé correspondant.
    """
    combined = " ".join(note_names + descriptions).lower()
    scored = [
        (b, sum(1 for kw in _BOOSTER_KEYWORDS.get(b["name"], []) if kw in combined))
        for b in boosters
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


_ML_STEP = Decimal("0.1")  # les ml affichés/imprimés doivent être des multiples de 0.1 (1.1, 1.2... jamais 1.13)
_ML_MIN = Decimal("1.0")   # en dessous, une note n'est pas dosable de façon fiable en flacon


def _distribute_ml(total_ml: float | int, count: int) -> list[float]:
    """Répartit `total_ml` en `count` valeurs, chacune un multiple de 0.1 ml et jamais
    sous 1.0 ml. Si `total_ml / count` est déjà sous 1.0 ml (catégorie sous-dotée par la
    config de taille), le minimum de 1.0 ml prime sur le budget de la catégorie — mieux
    vaut une formule légèrement plus généreuse que des doses non réalisables en pratique.
    """
    if count <= 0:
        return []

    total = Decimal(str(total_ml))
    effective_total = max(total, _ML_MIN * count)

    # Travaille en "pas de 0.1 ml" (entiers) pour répartir le reste sans erreur d'arrondi.
    steps_total = (effective_total / _ML_STEP).quantize(Decimal("1"), rounding=ROUND_DOWN)
    min_steps = (_ML_MIN / _ML_STEP).quantize(Decimal("1"))
    base_steps = max(min_steps, (steps_total / count).quantize(Decimal("1"), rounding=ROUND_DOWN))
    remainder = int(steps_total - (base_steps * count))

    values = []
    for index in range(count):
        extra = 1 if index < remainder else 0
        steps = int(base_steps) + extra
        values.append(float((Decimal(steps) * _ML_STEP).quantize(_ML_STEP)))
    return values


def _extract_note_name(raw) -> str:
    """Le LLM doit renvoyer {"name": ..., "alternatives": [...]}, mais on reste tolérant
    s'il renvoie encore un simple string (ancien format / écart au schéma)."""
    if isinstance(raw, dict):
        return str(raw.get("name", "")).strip()
    return str(raw).strip()


def _extract_note_alternatives(raw) -> list[str]:
    if isinstance(raw, dict):
        return [str(a).strip() for a in raw.get("alternatives", []) if str(a).strip()]
    return []


def _build_note_entries(
    note_names: list[str],
    total_ml: float | int,
    alternatives_by_name: dict[str, list[str]] | None = None,
) -> list[dict]:
    distributed_ml = _distribute_ml(total_ml, len(note_names))
    alternatives_by_name = alternatives_by_name or {}
    entries = []
    for name, ml in zip(note_names, distributed_ml, strict=False):
        entry = {"name": name, "ml": ml}
        alt_names = alternatives_by_name.get(name)
        if alt_names:
            # Même dosage que la note principale : une alternative est un remplacement
            # 1-pour-1, elle occupe la même place dans la formule.
            entry["alternatives"] = [{"name": alt, "ml": ml} for alt in alt_names]
        entries.append(entry)
    return entries


def _normalize_note_list(
    requested_notes: list,
    available_names: list[str],
    target_count: int,
    score_by_name: dict[str, int] | None = None,
    reject_score: int = 0,
) -> tuple[list[str], dict[str, list[str]]]:
    """Retourne (noms retenus, alternatives normalisées par nom retenu).

    Une alternative n'est gardée que si elle existe dans le catalogue disponible et
    n'est ni la note elle-même, ni une note déjà retenue ailleurs dans la formule —
    sinon elle est ignorée silencieusement (mieux vaut 0-1 alternative fiable que 2
    alternatives inventées par le LLM).

    `score_by_name` (positif = intense, négatif = léger, voir `_note_intensity_score`)
    et `reject_score` filtrent les choix du LLM : le LLM ignore parfois sa consigne de
    registre (ex : glisse une note "fraîche" dans une formule "puissant") — un simple
    prompt ne suffit pas à le garantir de façon fiable, donc on rejette ici toute note
    dont le score franchit `reject_score` dans le mauvais sens, et on repêche une note
    cohérente parmi les candidats disponibles restants (triés par score, meilleur en
    premier) plutôt que d'accepter le choix du LLM tel quel.
    """
    available_lookup = {name.lower(): name for name in available_names}
    selected: list[str] = []
    seen: set[str] = set()
    alternatives: dict[str, list[str]] = {}
    score_by_name = score_by_name or {}

    def rejected(name: str) -> bool:
        if not score_by_name:
            return False
        score = score_by_name.get(name, 0)
        if reject_score > 0:
            return score < reject_score  # registre "intense" attendu, note trop légère
        if reject_score < 0:
            return score > reject_score  # registre "léger" attendu, note trop intense
        return False

    for raw in requested_notes:
        normalized = available_lookup.get(_extract_note_name(raw).lower())
        if not normalized or normalized in seen or rejected(normalized):
            continue
        selected.append(normalized)
        seen.add(normalized)

        alt_names: list[str] = []
        for raw_alt in _extract_note_alternatives(raw):
            alt_normalized = available_lookup.get(raw_alt.lower())
            if (
                not alt_normalized or alt_normalized == normalized or alt_normalized in seen
                or alt_normalized in alt_names or rejected(alt_normalized)
            ):
                continue
            alt_names.append(alt_normalized)
            if len(alt_names) == 2:
                break
        if alt_names:
            alternatives[normalized] = alt_names

        if len(selected) == target_count:
            break

    if len(selected) < target_count:
        # Repêchage : notes disponibles non retenues, triées par cohérence avec le registre
        # demandé (meilleur score en premier) plutôt que dans l'ordre brut du catalogue.
        remaining = [name for name in available_names if name not in seen]
        remaining.sort(key=lambda n: score_by_name.get(n, 0), reverse=(reject_score > 0))
        for name in remaining:
            selected.append(name)
            seen.add(name)
            if len(selected) == target_count:
                break

    _ensure_each_note_has_an_alternative(selected, alternatives, available_names, seen)
    return selected, alternatives


def _ensure_each_note_has_an_alternative(
    selected: list[str],
    alternatives: dict[str, list[str]],
    available_names: list[str],
    seen: set[str],
) -> None:
    """Garantit qu'AUCUNE note retenue ne se retrouve sans alternative — que ce soit parce
    que le LLM n'en a proposé aucune de valide, ou parce que la note vient du repêchage
    (qui n'en fournit jamais). Mieux vaut une alternative choisie au hasard dans le
    catalogue restant qu'aucune : "on sait jamais", il faut toujours une porte de sortie
    si le client n'aime pas une note. Modifie `alternatives` et `seen` en place.
    """
    for name in selected:
        if alternatives.get(name):
            continue
        # Candidates : notes du catalogue disponible, jamais utilisées ailleurs dans
        # cette formule (ni comme note principale, ni déjà comme alternative d'une autre).
        used_as_alt = {a for alts in alternatives.values() for a in alts}
        candidates = [n for n in available_names if n not in seen and n not in used_as_alt]
        if not candidates:
            # Catalogue épuisé (rare, box très restreinte) : aucune alternative possible.
            continue
        alternatives[name] = [candidates[0]]


# Seuil de rejet passé à `_normalize_note_list` par type de formule : "puissant" rejette
# les notes au score négatif (trop légères), "frais" rejette celles au score positif
# (trop intenses), "mix" ne filtre pas (0 désactive le filtre, cf. `rejected()`).
_FORMULA_TYPE_REJECT_SCORE = {"frais": -1, "mix": 0, "puissant": 1}


def _normalize_formula_notes(
    llm_result: dict,
    ingredients: list[dict],
    formula_type: str,
) -> tuple[list[str], list[str], list[str], dict[str, list[str]]]:
    counts = _FORMULA_TYPE_CONFIGS[formula_type]["note_counts"]
    available_by_type = {
        "top": [ing["name"] for ing in ingredients if ing["type"] == "top"],
        "heart": [ing["name"] for ing in ingredients if ing["type"] == "heart"],
        "base": [ing["name"] for ing in ingredients if ing["type"] == "base"],
    }
    score_by_name = {ing["name"]: _note_intensity_score(ing["name"], ing.get("description", "")) for ing in ingredients}
    reject_score = _FORMULA_TYPE_REJECT_SCORE.get(formula_type, 0)

    top_notes, top_alts = _normalize_note_list(
        llm_result.get("top_notes", []), available_by_type["top"], counts["top"], score_by_name, reject_score
    )
    heart_notes, heart_alts = _normalize_note_list(
        llm_result.get("heart_notes", []), available_by_type["heart"], counts["heart"], score_by_name, reject_score
    )
    base_notes, base_alts = _normalize_note_list(
        llm_result.get("base_notes", []), available_by_type["base"], counts["base"], score_by_name, reject_score
    )
    alternatives_by_name = {**top_alts, **heart_alts, **base_alts}
    return top_notes, heart_notes, base_notes, alternatives_by_name


def _compute_sizes(
    top_notes: list[str],
    heart_notes: list[str],
    base_notes: list[str],
    booster: dict,
    formula_type: str,
    alternatives_by_name: dict[str, list[str]] | None = None,
) -> dict:
    config = _FORMULA_TYPE_CONFIGS[formula_type]["sizes"]
    sizes = {}
    for target_ml, ml_config in config.items():
        sizes[f"{target_ml}ml"] = {
            "target_ml": target_ml,
            "formula_type": formula_type,
            "top_notes": _build_note_entries(top_notes, ml_config["top_ml"], alternatives_by_name),
            "heart_notes": _build_note_entries(heart_notes, ml_config["heart_ml"], alternatives_by_name),
            "base_notes": _build_note_entries(base_notes, ml_config["base_ml"], alternatives_by_name),
            "boosters": [{"name": booster["name"], "ml": ml_config["booster_ml"]}],
        }
    return sizes


# ── Construction d'une formule ────────────────────────────────────────

# Mots-clés de familles olfactives, classés par registre — sert à vérifier qu'une
# description générée par le LLM ne contredit pas le registre réel de la formule
# (hallucination constatée en test : le LLM a décrit "la profondeur du cuir" pour une
# formule qui n'avait aucune note cuirée/boisée, ou l'inverse pour une formule "frais").
# On ne cherche PAS une correspondance mot-à-mot avec les descriptions catalogue (trop
# fragile face au vocabulaire varié du LLM) : seule la contradiction de REGISTRE compte.
_INTENSE_FAMILY_KEYWORDS = [
    "boisé", "boisee", "bois", "ambre", "ambré", "ambree", "cuir", "musc", "musqué",
    "épicé", "epice", "épice", "oriental", "tabac", "vanille", "patchouli", "oud",
    "résine", "resine", "encens", "animale", "capiteux", "capiteuse",
]
_LIGHT_FAMILY_KEYWORDS = [
    "agrume", "citron", "bergamote", "pamplemousse", "aquatique", "marin", "brise",
    "aldéhyd", "aleyhyd", "vert", "verte", "pétillant", "petillant", "léger", "legere",
    "légèreté", "legerete", "fraîcheur", "fraicheur", "fraîche", "fraiche", "discret",
]


def _mentioned_register(text: str) -> str | None:
    """"intense", "light" ou None selon les mots-clés dominants du texte."""
    lowered = text.lower()
    intense_hits = sum(1 for kw in _INTENSE_FAMILY_KEYWORDS if kw in lowered)
    light_hits = sum(1 for kw in _LIGHT_FAMILY_KEYWORDS if kw in lowered)
    if intense_hits and not light_hits:
        return "intense"
    if light_hits and not intense_hits:
        return "light"
    return None  # mixte ou neutre : pas de contradiction possible à détecter ici


def _description_is_consistent(description: str, formula_type: str) -> bool:
    """Rejette une description dont le registre olfactif contredit franchement le
    formula_type réel (ex : description "légère"/"fraîche" pour une formule "puissant",
    ou l'inverse) — la protection sur les notes elles-mêmes se fait en amont, dans le
    filtrage de `_normalize_note_list` ; ceci ne couvre que le texte de la description."""
    if not description:
        return False
    described = _mentioned_register(description)
    if described is None:
        return True
    if formula_type == "puissant" and described == "light":
        return False
    if formula_type == "frais" and described == "intense":
        return False
    return True


def _fallback_description(note_names: list[str], note_descriptions: list[str], formula_type: str, language: str) -> str:
    """Description de secours, écrite pour rester fidèle au formula_type réel (jamais
    de contradiction possible), utilisée quand celle du LLM échoue la vérification
    ci-dessus."""
    if language == "fr":
        register = {"frais": "léger et frais", "puissant": "intense et capiteux", "mix": "équilibré"}.get(formula_type, "équilibré")
        payoff = {"frais": "une fraîcheur discrète", "puissant": "un sillage marquant et durable", "mix": "une harmonie subtile"}.get(formula_type, "une harmonie subtile")
        return f"Un parfum {register}, composé de notes sélectionnées avec soin pour révéler {payoff}."
    register = {"frais": "light and fresh", "puissant": "intense and rich", "mix": "balanced"}.get(formula_type, "balanced")
    payoff = {"frais": "a subtle freshness", "puissant": "a bold, lasting trail", "mix": "a subtle harmony"}.get(formula_type, "a subtle harmony")
    return f"A {register} fragrance, composed of carefully selected notes to reveal {payoff}."


def _finalize_formula(
    llm_result: dict,
    ingredients: list[dict],
    boosters: list[dict],
    excluded_names: set[str],
    language: str = "fr",
) -> dict:
    """Post-traite un résultat LLM brut en formule complète (notes normalisées, booster, ml).

    `excluded_names` sert de filet de sécurité pour éviter qu'une note déjà utilisée
    par une autre formule du même lot ne soit réutilisée telle quelle si le LLM n'a
    pas respecté la consigne de diversité.
    """
    profile = llm_result.get("profile", "Visionary")
    profile_description = llm_result.get("profile_description", "")
    formula_type = llm_result.get("formula_type", "mix")
    if formula_type not in _FORMULA_TYPE_CONFIGS:
        formula_type = "mix"

    available_ingredients = [i for i in ingredients if i["name"] not in excluded_names]
    top_notes, heart_notes, base_notes, alternatives_by_name = _normalize_formula_notes(
        llm_result, available_ingredients, formula_type
    )

    all_names = top_notes + heart_notes + base_notes
    ing_by_name = {i["name"]: i for i in ingredients}
    descriptions = [ing_by_name[n]["description"] for n in all_names if n in ing_by_name]

    # Le filtrage d'intensité ci-dessus peut avoir remplacé les notes choisies par le
    # LLM (note rejetée + repêchage) : sa description, écrite pour son choix initial,
    # peut donc contredire le registre réel de la formule finale (déjà observé en test :
    # description "légère"/"fraîche" alors que le formula_type réel est "puissant"). On
    # vérifie et on retombe sur une description neutre, fidèle au formula_type, si besoin.
    if not _description_is_consistent(profile_description, formula_type):
        profile_description = _fallback_description(all_names, descriptions, formula_type, language)

    booster = _select_booster(all_names, descriptions, boosters)
    sizes = _compute_sizes(top_notes, heart_notes, base_notes, booster, formula_type, alternatives_by_name)

    return {
        "profile": profile,
        "formula_type": formula_type,
        "description": profile_description,
        "top_notes": top_notes,
        "heart_notes": heart_notes,
        "base_notes": base_notes,
        "sizes": sizes,
        "_selected_names": set(all_names),
    }


async def _build_formula(
    answers: dict,
    ingredients: list[dict],
    boosters: list[dict],
    user_allergens: list[str] | None,
    excluded_names: set[str],
    excluded_profiles: set[str],
    language: str,
    force_type: str | None,
) -> dict:
    llm_result = await _ask_llm_for_formula(
        answers, ingredients, user_allergens, excluded_names, excluded_profiles, language, force_type
    )
    return _finalize_formula(llm_result, ingredients, boosters, excluded_names, language)


async def _build_formulas(
    answers: dict,
    ingredients: list[dict],
    boosters: list[dict],
    user_allergens: list[str] | None,
    language: str,
    force_type: str | None,
    formula_count: int = 2,
) -> list[dict]:
    """Génère plusieurs formules en UN SEUL appel LLM (au lieu d'un appel séquentiel par formule)."""
    llm_results = await _ask_llm_for_formulas(
        answers, ingredients, user_allergens, language, force_type, formula_count
    )

    formulas = []
    excluded_names: set[str] = set()
    for llm_result in llm_results:
        formula = _finalize_formula(llm_result, ingredients, boosters, excluded_names, language)
        excluded_names |= formula["_selected_names"]
        formulas.append(formula)
    return formulas


# ── Génération des formules ───────────────────────────────────────────

async def generate_formulas(session_id: str, force_type: str | None = None) -> dict:
    session_data = session_store.get_session_answers(session_id)
    if not session_data or not session_data.get("answers"):
        return {"error": "Aucune réponse trouvée", "formulas": []}

    session_meta = session_store.get_session_meta(session_id)
    language = session_meta.get("language", "fr") if session_meta else "fr"

    profile = session_store.get_user_profile(session_id)
    has_allergies = profile.get("has_allergies", "non") if profile else "non"
    user_allergens_raw = profile.get("allergies", "") if profile else ""

    user_allergens = None
    if has_allergies in ("oui", "yes") and user_allergens_raw:
        user_allergens = [a.strip() for a in user_allergens_raw.replace(",", ";").split(";") if a.strip()]

    # Les deux appels sont indépendants (endpoint/params différents) : on les lance
    # en parallèle plutôt qu'en série pour ne payer qu'une seule latence réseau.
    ingredients, boosters = await asyncio.gather(
        _load_ingredients_from_db(language), _load_boosters_with_fallback(language)
    )
    if not ingredients:
        return {"error": "Aucun ingrédient disponible en base de données", "formulas": []}

    # Un seul appel LLM génère les 2 formules d'un coup (au lieu de 2 appels séquentiels) :
    # ça garantit nativement leur diversité et divise par 2 la latence de cette étape.
    formulas = await _build_formulas(
        session_data["answers"], ingredients, boosters, user_allergens, language, force_type,
    )
    for formula in formulas:
        formula.pop("_selected_names", None)
        # TODO: moodboard temporairement désactivé pour accélérer la génération (voir formula_service.py)
        # formula = await moodboard_service.attach_moodboard_safe(formula, language)

    session_store.save_generated_formulas(session_id, formulas)
    return {"formulas": formulas}


async def generate_formulas_stateless(
    answers: dict,
    language: str = "fr",
    has_allergies: str = "non",
    user_allergens_raw: str = "",
    force_type: str | None = None,
) -> dict:
    if not answers:
        return {"error": "Aucune réponse fournie", "formulas": []}

    user_allergens = None
    if has_allergies in ("oui", "yes") and user_allergens_raw:
        user_allergens = [a.strip() for a in user_allergens_raw.replace(",", ";").split(";") if a.strip()]

    # Les deux appels sont indépendants (endpoint/params différents) : on les lance
    # en parallèle plutôt qu'en série pour ne payer qu'une seule latence réseau.
    ingredients, boosters = await asyncio.gather(
        _load_ingredients_from_db(language), _load_boosters_with_fallback(language)
    )
    if not ingredients:
        return {"error": "Aucun ingrédient disponible en base de données", "formulas": []}

    # Un seul appel LLM génère les 2 formules d'un coup (au lieu de 2 appels séquentiels) :
    # ça garantit nativement leur diversité et divise par 2 la latence de cette étape.
    formulas = await _build_formulas(
        answers, ingredients, boosters, user_allergens, language, force_type,
    )
    for formula in formulas:
        formula.pop("_selected_names", None)
        # TODO: moodboard temporairement désactivé pour accélérer la génération (voir formula_service.py)
        # formula = await moodboard_service.attach_moodboard_safe(formula, language)

    return {"formulas": formulas}


# ── Sélection et personnalisation ─────────────────────────────────────

def select_formula(session_id: str, formula_index: int) -> dict:
    formulas = session_store.get_generated_formulas(session_id)
    if not formulas:
        return {"error": "No generated formulas found"}
    if formula_index not in (0, 1):
        return {"error": "formula_index must be 0 or 1"}
    if formula_index >= len(formulas):
        return {"error": "Invalid formula index"}
    selected = formulas[formula_index]
    session_store.save_selected_formula(session_id, selected)
    return {"formula": selected}


async def change_selected_formula_type(session_id: str, formula_type: str) -> dict:
    if formula_type not in _FORMULA_TYPE_CONFIGS:
        return {"error": f"formula_type must be one of: {', '.join(_FORMULA_TYPE_CONFIGS)}"}

    session_data = session_store.get_session_answers(session_id)
    if not session_data or not session_data.get("answers"):
        return {"error": "Aucune réponse trouvée"}

    session_meta = session_store.get_session_meta(session_id)
    language = session_meta.get("language", "fr") if session_meta else "fr"

    profile = session_store.get_user_profile(session_id)
    has_allergies = profile.get("has_allergies", "non") if profile else "non"
    user_allergens_raw = profile.get("allergies", "") if profile else ""

    user_allergens = None
    if has_allergies in ("oui", "yes") and user_allergens_raw:
        user_allergens = [a.strip() for a in user_allergens_raw.replace(",", ";").split(";") if a.strip()]

    # Les deux appels sont indépendants (endpoint/params différents) : on les lance
    # en parallèle plutôt qu'en série pour ne payer qu'une seule latence réseau.
    ingredients, boosters = await asyncio.gather(
        _load_ingredients_from_db(language), _load_boosters_with_fallback(language)
    )
    if not ingredients:
        return {"error": "Aucun ingrédient disponible en base de données"}

    formula = await _build_formula(
        session_data["answers"], ingredients, boosters, user_allergens,
        set(), set(), language, force_type=formula_type
    )
    formula.pop("_selected_names", None)
    # TODO: moodboard temporairement désactivé pour accélérer la génération (voir formula_service.py)
    # formula = await moodboard_service.attach_moodboard_safe(formula, language)
    session_store.save_selected_formula(session_id, formula)
    return {"formula": formula}


async def get_available_ingredients(session_id: str, note_type: str) -> dict:
    if note_type not in ("top", "heart", "base"):
        return {"error": "note_type must be top, heart, or base"}

    session_meta = session_store.get_session_meta(session_id)
    language = session_meta.get("language", "fr") if session_meta else "fr"

    profile = session_store.get_user_profile(session_id)
    has_allergies = profile.get("has_allergies", "non") if profile else "non"
    user_allergens_raw = profile.get("allergies", "") if profile else ""

    user_allergens = None
    if has_allergies in ("oui", "yes") and user_allergens_raw:
        user_allergens = [a.strip() for a in user_allergens_raw.replace(",", ";").split(";") if a.strip()]

    ingredients = await _load_ingredients_from_db(language)

    selected = session_store.get_selected_formula(session_id)
    already_in_formula: set[str] = set()
    if selected:
        note_key = {"top": "top_notes", "heart": "heart_notes", "base": "base_notes"}[note_type]
        already_in_formula = {n.lower() for n in selected.get(note_key, [])}

    result = []
    for ing in ingredients:
        if ing["type"] != note_type:
            continue
        if ing["name"].lower() in already_in_formula:
            continue
        # Filtre allergènes si renseignés
        if user_allergens and ing["allergens"]:
            user_set = {a.lower() for a in user_allergens}
            ing_set = {a.lower() for a in ing["allergens"]}
            if user_set & ing_set:
                continue
        result.append({"name": ing["name"], "description": ing["description"]})

    return {"note_type": note_type, "ingredients": result}


async def replace_note(session_id: str, note_type: str, old_note: str, new_note: str) -> dict:
    if note_type not in ("top", "heart", "base"):
        return {"error": "note_type must be top, heart, or base"}

    selected = session_store.get_selected_formula(session_id)
    if not selected:
        return {"error": "No formula selected yet"}

    note_key = {"top": "top_notes", "heart": "heart_notes", "base": "base_notes"}[note_type]
    formula_type = selected.get("formula_type", "mix")

    notes = selected.get(note_key, [])
    found = False
    for i, name in enumerate(notes):
        if name.lower() == old_note.lower():
            notes[i] = new_note
            found = True
            break

    if not found:
        return {"error": f"Note '{old_note}' not found in current formula's {note_key}"}

    selected[note_key] = notes

    # Recalculer les ml (on conserve le booster déjà choisi pour cette formule)
    booster_name = selected.get("sizes", {}).get("30ml", {}).get("boosters", [{}])[0].get("name", _FALLBACK_BOOSTER["name"])
    booster = {"name": booster_name}
    selected["sizes"] = _compute_sizes(
        selected.get("top_notes", []),
        selected.get("heart_notes", []),
        selected.get("base_notes", []),
        booster,
        formula_type,
    )
    session_meta = session_store.get_session_meta(session_id)
    language = session_meta.get("language", "fr") if session_meta else "fr"
    # TODO: moodboard temporairement désactivé pour accélérer la génération (voir formula_service.py)
    # selected = await moodboard_service.attach_moodboard_safe(selected, language)

    session_store.save_selected_formula(session_id, selected)
    return {"formula": selected}


async def replace_note_stateless(formula: dict, note_type: str, old_note: str, new_note: str, language: str = "fr") -> dict:
    """Équivalent de replace_note() sans session serveur active : prend/rend la formule
    complète, utilisé par l'écran de personnalisation visuelle (mode quiz). Contrairement
    à replace_note(), le booster est ici RECALCULÉ pour rester cohérent avec les notes
    résultantes plutôt que de conserver celui de la sélection initiale.

    Le groupe {note active, alternatives} est un trio FIXE décidé à la génération : changer
    de note active ne fait que permuter laquelle des 3 est "active" — old_note rejoint le
    groupe d'alternatives de new_note. Aucune nouvelle alternative n'est générée, ce qui
    permet à l'utilisateur de naviguer librement entre les 3 options autant de fois qu'il veut.
    """
    if note_type not in ("top", "heart", "base"):
        return {"error": "note_type must be top, heart, or base"}

    note_key = {"top": "top_notes", "heart": "heart_notes", "base": "base_notes"}[note_type]
    formula_type = formula.get("formula_type", "mix")

    # Retrouve le trio (note active + ses alternatives) de old_note avant de le perdre.
    trio_names: list[str] | None = None
    for size_data in formula.get("sizes", {}).values():
        for entry in size_data.get(note_key, []):
            if isinstance(entry, dict) and entry.get("name", "").lower() == old_note.lower():
                trio_names = [entry["name"]] + [a["name"] for a in entry.get("alternatives", [])]
        if trio_names:
            break

    notes = list(formula.get(note_key, []))
    found = False
    for i, name in enumerate(notes):
        if name.lower() == old_note.lower():
            notes[i] = new_note
            found = True
            break
    if not found:
        return {"error": f"Note '{old_note}' not found in current formula's {note_key}"}

    updated = dict(formula)
    updated[note_key] = notes

    ingredients = await _load_ingredients_from_db(language)
    boosters = await _load_boosters_with_fallback(language)

    top_notes = updated.get("top_notes", [])
    heart_notes = updated.get("heart_notes", [])
    base_notes = updated.get("base_notes", [])
    all_names = top_notes + heart_notes + base_notes
    ing_by_name = {ing["name"]: ing for ing in ingredients}
    descriptions = [ing_by_name[n]["description"] for n in all_names if n in ing_by_name]
    booster = _select_booster(all_names, descriptions, boosters)

    # Conserve les alternatives des notes non touchées (issues de la génération initiale
    # par le LLM). Pour la note qui vient d'être insérée : son groupe d'alternatives est le
    # même trio qu'avant, moins elle-même (donc old_note + l'alternative non choisie).
    alternatives_by_name: dict[str, list[str]] = {}
    for size_data in formula.get("sizes", {}).values():
        for key in ("top_notes", "heart_notes", "base_notes"):
            for entry in size_data.get(key, []):
                if isinstance(entry, dict) and entry.get("alternatives") and entry["name"] in all_names:
                    alternatives_by_name[entry["name"]] = [a["name"] for a in entry["alternatives"]]
        break  # les alternatives sont identiques sur toutes les tailles, une seule suffit
    if trio_names and new_note in trio_names:
        alternatives_by_name[new_note] = [n for n in trio_names if n != new_note]

    # Filet de sécurité : si new_note n'appartenait pas au trio d'origine (ne devrait pas
    # arriver via le front, qui ne propose que les alternatives du trio, mais l'API accepte
    # n'importe quel new_note), elle se retrouverait sans alternative — jamais souhaitable.
    available_by_type = {
        "top": [ing["name"] for ing in ingredients if ing["type"] == "top"],
        "heart": [ing["name"] for ing in ingredients if ing["type"] == "heart"],
        "base": [ing["name"] for ing in ingredients if ing["type"] == "base"],
    }
    _ensure_each_note_has_an_alternative(
        [new_note], alternatives_by_name, available_by_type[note_type], set(all_names)
    )

    updated["sizes"] = _compute_sizes(top_notes, heart_notes, base_notes, booster, formula_type, alternatives_by_name)
    return {"formula": updated}
