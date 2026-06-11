"""Service de génération de formules de parfum.

Architecture :
  1. Récupère les ingrédients depuis la BDD (filtrés par langue/catégorie)
  2. Envoie au LLM les réponses + ingrédients disponibles
  3. Le LLM sélectionne les notes, déduit le profil et le type de formule
  4. Calcul des ml selon le tableau des formules (inchangé)
"""

import json
from decimal import Decimal, ROUND_DOWN

from openai import AsyncOpenAI

from app.config import get_settings
from app.database.connection import AsyncSessionLocal
from app.database import crud
from app.services import session_store

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

BOOSTERS = [
    {
        "name": "Floral",
        "keywords": ["fleur", "rose", "jasmin", "muguet", "floral", "flower",
                     "pétale", "bouquet", "pivoine", "iris", "ylang",
                     "néroli", "magnolia", "tubéreuse", "gardénia"],
    },
    {
        "name": "Ambre doux",
        "keywords": ["ambre", "vanille", "oriental", "chaud", "doux", "warm",
                     "amber", "gourmand", "caramel", "miel", "tonka",
                     "baume", "résine", "encens", "oud", "boisé"],
    },
    {
        "name": "Musc blanc sec",
        "keywords": ["musc", "propre", "frais", "clean", "musk", "coton",
                     "savon", "linge", "poudré", "aldéhyde", "blanc",
                     "minéral", "ozonic", "aquatique", "agrume",
                     "bergamote", "citron", "pamplemousse"],
    },
]


# ── Chargement des ingrédients depuis la BDD ──────────────────────────

async def _load_ingredients_from_db(language: str, category: str | None = None) -> list[dict]:
    async with AsyncSessionLocal() as db:
        ingredients = await crud.get_all_ingredients(db, language=language, category=category, active_only=True)
    return [
        {
            "id": i.id,
            "name": i.name,
            "type": i.type,
            "description": i.description or "",
            "intensity": i.intensity or "",
            "allergens": i.allergens,
        }
        for i in ingredients
    ]


# ── Appel LLM ────────────────────────────────────────────────────────

async def _ask_llm_for_formula(
    answers: dict,
    ingredients: list[dict],
    user_allergens: list[str] | None,
    excluded_names: set[str],
    excluded_profiles: set[str],
    language: str,
    force_type: str | None,
) -> dict:
    """Demande au LLM de sélectionner les notes et de déduire le profil."""

    client = AsyncOpenAI(api_key=get_settings().openai_api_key)

    # Filtrer les ingrédients déjà utilisés
    available = [i for i in ingredients if i["name"] not in excluded_names]

    # Construire la liste des ingrédients par type pour le prompt
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

    force_type_instruction = ""
    if force_type and force_type in _FORMULA_TYPE_CONFIGS:
        counts = _FORMULA_TYPE_CONFIGS[force_type]["note_counts"]
        force_type_instruction = f'Le type de formule est imposé : "{force_type}". Sélectionne exactement {counts["top"]} notes de tête, {counts["heart"]} notes de cœur et {counts["base"]} notes de fond.'
    else:
        force_type_instruction = """Déduis le type de formule le plus adapté au profil :
- "frais" : 3 notes de tête, 3 de cœur, 2 de fond (profils féminins légers)
- "mix" : 2 notes de tête, 3 de cœur, 2 de fond (profils unisexes)
- "puissant" : 2 notes de tête, 2 de cœur, 3 de fond (profils masculins intenses)"""

    system_prompt = f"""Tu es un expert en parfumerie. Tu dois créer une formule de parfum personnalisée pour un client en analysant ses réponses à un questionnaire olfactif.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, dans ce format exact :
{{
  "profile": "nom du profil olfactif (ex: Visionary, Creator, Icon, Disruptor, Trailblazer, Innovator, Strategist, Influencer, Cosy)",
  "profile_description": "description courte et poétique du profil en {'français' if language == 'fr' else 'anglais'} (2-3 phrases)",
  "formula_type": "frais | mix | puissant",
  "top_notes": ["note1", "note2"],
  "heart_notes": ["note1", "note2", "note3"],
  "base_notes": ["note1", "note2"]
}}

Les noms des notes doivent correspondre EXACTEMENT aux noms disponibles dans la liste fournie."""

    user_prompt = f"""Voici les réponses du client au questionnaire :
{chr(10).join(answers_summary)}

Notes de tête disponibles :
{format_ingredients('top')}

Notes de cœur disponibles :
{format_ingredients('heart')}

Notes de fond disponibles :
{format_ingredients('base')}

{allergen_instruction}
{excluded_profiles_instruction}
{force_type_instruction}

Sélectionne les notes les plus cohérentes avec les préférences du client et crée une formule harmonieuse."""

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


# ── Calcul des quantités en ml ────────────────────────────────────────

def _select_booster(note_names: list[str], descriptions: list[str]) -> dict:
    combined = " ".join(note_names + descriptions).lower()
    scored = [(b, sum(1 for kw in b["keywords"] if kw in combined)) for b in BOOSTERS]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def _distribute_ml(total_ml: float | int, count: int) -> list[float]:
    if count <= 0:
        return []

    total = Decimal(str(total_ml))
    cents = (total * 100).quantize(Decimal("1"))
    base = (cents / count).quantize(Decimal("1"), rounding=ROUND_DOWN)
    remainder = int(cents - (base * count))

    values = []
    for index in range(count):
        extra = Decimal("1") if index < remainder else Decimal("0")
        values.append(float((base + extra) / 100))
    return values


def _build_note_entries(note_names: list[str], total_ml: float | int) -> list[dict]:
    distributed_ml = _distribute_ml(total_ml, len(note_names))
    return [
        {"name": name, "ml": ml}
        for name, ml in zip(note_names, distributed_ml, strict=False)
    ]


def _normalize_note_list(
    requested_notes: list[str],
    available_names: list[str],
    target_count: int,
) -> list[str]:
    available_lookup = {name.lower(): name for name in available_names}
    selected: list[str] = []
    seen: set[str] = set()

    for raw_name in requested_notes:
        normalized = available_lookup.get(str(raw_name).strip().lower())
        if not normalized or normalized in seen:
            continue
        selected.append(normalized)
        seen.add(normalized)
        if len(selected) == target_count:
            return selected

    for name in available_names:
        if name in seen:
            continue
        selected.append(name)
        seen.add(name)
        if len(selected) == target_count:
            break

    return selected


def _normalize_formula_notes(
    llm_result: dict,
    ingredients: list[dict],
    formula_type: str,
) -> tuple[list[str], list[str], list[str]]:
    counts = _FORMULA_TYPE_CONFIGS[formula_type]["note_counts"]
    available_by_type = {
        "top": [ing["name"] for ing in ingredients if ing["type"] == "top"],
        "heart": [ing["name"] for ing in ingredients if ing["type"] == "heart"],
        "base": [ing["name"] for ing in ingredients if ing["type"] == "base"],
    }

    top_notes = _normalize_note_list(llm_result.get("top_notes", []), available_by_type["top"], counts["top"])
    heart_notes = _normalize_note_list(llm_result.get("heart_notes", []), available_by_type["heart"], counts["heart"])
    base_notes = _normalize_note_list(llm_result.get("base_notes", []), available_by_type["base"], counts["base"])
    return top_notes, heart_notes, base_notes


def _compute_sizes(
    top_notes: list[str],
    heart_notes: list[str],
    base_notes: list[str],
    booster: dict,
    formula_type: str,
) -> dict:
    config = _FORMULA_TYPE_CONFIGS[formula_type]["sizes"]
    sizes = {}
    for target_ml, ml_config in config.items():
        sizes[f"{target_ml}ml"] = {
            "target_ml": target_ml,
            "formula_type": formula_type,
            "top_notes": _build_note_entries(top_notes, ml_config["top_ml"]),
            "heart_notes": _build_note_entries(heart_notes, ml_config["heart_ml"]),
            "base_notes": _build_note_entries(base_notes, ml_config["base_ml"]),
            "boosters": [{"name": booster["name"], "ml": ml_config["booster_ml"]}],
        }
    return sizes


# ── Construction d'une formule ────────────────────────────────────────

async def _build_formula(
    answers: dict,
    ingredients: list[dict],
    user_allergens: list[str] | None,
    excluded_names: set[str],
    excluded_profiles: set[str],
    language: str,
    force_type: str | None,
) -> dict:
    llm_result = await _ask_llm_for_formula(
        answers, ingredients, user_allergens, excluded_names, excluded_profiles, language, force_type
    )

    profile = llm_result.get("profile", "Visionary")
    profile_description = llm_result.get("profile_description", "")
    formula_type = llm_result.get("formula_type", "mix")
    if formula_type not in _FORMULA_TYPE_CONFIGS:
        formula_type = "mix"

    top_notes, heart_notes, base_notes = _normalize_formula_notes(llm_result, ingredients, formula_type)

    all_names = top_notes + heart_notes + base_notes
    ing_by_name = {i["name"]: i for i in ingredients}
    descriptions = [ing_by_name[n]["description"] for n in all_names if n in ing_by_name]

    booster = _select_booster(all_names, descriptions)
    sizes = _compute_sizes(top_notes, heart_notes, base_notes, booster, formula_type)

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

    ingredients = await _load_ingredients_from_db(language)
    if not ingredients:
        return {"error": "Aucun ingrédient disponible en base de données", "formulas": []}

    formulas = []
    excluded_names: set[str] = set()
    excluded_profiles: set[str] = set()

    for _ in range(2):
        formula = await _build_formula(
            session_data["answers"], ingredients, user_allergens,
            excluded_names, excluded_profiles, language, force_type
        )
        excluded_names |= formula.pop("_selected_names", set())
        excluded_profiles.add(formula["profile"])
        formulas.append(formula)

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

    ingredients = await _load_ingredients_from_db(language)
    if not ingredients:
        return {"error": "Aucun ingrédient disponible en base de données", "formulas": []}

    formulas = []
    excluded_names: set[str] = set()
    excluded_profiles: set[str] = set()

    for _ in range(2):
        formula = await _build_formula(
            answers, ingredients, user_allergens,
            excluded_names, excluded_profiles, language, force_type
        )
        excluded_names |= formula.pop("_selected_names", set())
        excluded_profiles.add(formula["profile"])
        formulas.append(formula)

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

    ingredients = await _load_ingredients_from_db(language)
    if not ingredients:
        return {"error": "Aucun ingrédient disponible en base de données"}

    formula = await _build_formula(
        session_data["answers"], ingredients, user_allergens,
        set(), set(), language, force_type=formula_type
    )
    formula.pop("_selected_names", None)
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

    # Recalculer les ml
    booster_name = selected.get("sizes", {}).get("30ml", {}).get("boosters", [{}])[0].get("name", BOOSTERS[0]["name"])
    booster = next((b for b in BOOSTERS if b["name"] == booster_name), BOOSTERS[0])
    selected["sizes"] = _compute_sizes(
        selected.get("top_notes", []),
        selected.get("heart_notes", []),
        selected.get("base_notes", []),
        booster,
        formula_type,
    )

    session_store.save_selected_formula(session_id, selected)
    return {"formula": selected}
