"""Recherche de parfums du commerce ressemblant à une formule générée.

Contrairement à catalog_service (qui choisit parmi un catalogue Excel statique),
ici le LLM cherche sur le web de vrais parfums existants qui se rapprochent des
notes de la formule — on lui demande une source par parfum cité pour limiter le
risque d'hallucination (sans pour autant l'éliminer complètement).
"""

import json
import logging
from urllib.parse import urlparse

from openai import AsyncOpenAI

from app.config import get_settings
from app.core.languages import LANGUAGE_NAMES, SupportedLanguage

logger = logging.getLogger("lylo.similar_perfumes")

_MODEL = "gpt-4o-mini"
_COUNT = 2
_CANDIDATE_COUNT = 8  # demandé au LLM, pour garder une marge après filtrage des sources

# Enseignes de parfumerie grand public reconnues — toute URL source hors de ces domaines
# est rejetée, même si le LLM l'a proposée (filet de sécurité anti-hallucination/anti-niche,
# le prompt seul ne suffit pas à garantir que le LLM s'y tienne).
_ALLOWED_RETAILER_DOMAINS = (
    "sephora.fr", "sephora.com", "sephora.es", "sephora.de", "sephora.it", "sephora.ae",
    "marionnaud.fr", "marionnaud.be", "marionnaud.es",
    "nocibe.fr",
    "douglas.fr", "douglas.de", "douglas.es", "douglas.it", "douglas.nl", "douglas.at", "douglas.pl",
    "notino.fr", "notino.de", "notino.es", "notino.it",
    "parfumdreams.de",
    "ulta.com",
    "macys.com",
    "nordstrom.com",
    "boots.com",
    "lookfantastic.com",
)


def _is_allowed_source(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    host = host.removeprefix("www.")
    return any(host == d or host.endswith(f".{d}") for d in _ALLOWED_RETAILER_DOMAINS)


def _notes_summary(formula: dict) -> str:
    top = ", ".join(formula.get("top_notes") or [])
    heart = ", ".join(formula.get("heart_notes") or [])
    base = ", ".join(formula.get("base_notes") or [])
    lines = []
    if top:
        lines.append(f"Notes de tête : {top}")
    if heart:
        lines.append(f"Notes de cœur : {heart}")
    if base:
        lines.append(f"Notes de fond : {base}")
    return "\n".join(lines)


async def find_similar_perfumes(formula: dict, language: SupportedLanguage = "fr") -> dict:
    """Interroge un LLM avec recherche web pour trouver 2 parfums du commerce
    ressemblant à la formule donnée. Retourne {"similar_perfumes": [...]} ou
    {"error": "..."} si la formule n'a pas de notes exploitables."""
    notes_text = _notes_summary(formula)
    if not notes_text:
        return {"error": "Formule sans notes exploitables"}

    lang_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["fr"])
    profile = formula.get("profile") or formula.get("description") or ""

    instructions = f"""Tu es un expert en parfumerie. On te donne la composition d'une formule de parfum
sur-mesure. Cherche sur le web {_COUNT} parfums du commerce dont le profil olfactif se rapproche le
plus de cette formule.

Contrainte STRICTE : choisis uniquement des parfums de GRANDES MARQUES GRAND PUBLIC, du type de
celles vendues chez Sephora, Marionnaud, Nocibé, Douglas (ou équivalent local à la langue de la
réponse) — par exemple des marques comme Dior, Chanel, Yves Saint Laurent, Giorgio Armani, Lancôme,
Paco Rabanne, Jean Paul Gaultier, Hugo Boss, Versace, Carolina Herrera, Calvin Klein, Prada, Gucci,
Burberry, Valentino, Dolce & Gabbana, Azzaro, Montblanc, Narciso Rodriguez — ou toute autre marque
de ce même niveau de notoriété et de diffusion en parfumerie généraliste.

INTERDICTION ABSOLUE de proposer des marques niche, confidentielles, artisanales, indépendantes ou
vendues uniquement en parfumerie spécialisée/boutique de marque/en ligne spécialisé (par exemple :
pas de Houbigant, Orto Parisi, Bon Parfumeur, Al Majed Oud, Amouage, ou toute marque que tu ne
trouverais pas en rayon Sephora/Marionnaud/Nocibé/Douglas).

Pour chaque parfum, tu DOIS fournir une URL source qui est une fiche produit EXISTANTE sur le site
d'une enseigne de parfumerie grand public elle-même (ex. sephora.fr, marionnaud.fr, nocibe.fr,
douglas.fr, ou équivalent local à la langue de la réponse) — cette URL doit être le moyen de VÉRIFIER
que le parfum y est bien vendu. N'utilise JAMAIS comme source un site agrégateur/encyclopédie de
parfums (ex. Fragrantica, Parfumo), un blog, un comparateur de prix générique ou un revendeur que
tu ne reconnais pas comme une enseigne de parfumerie grand public reconnue.
N'invente JAMAIS un parfum ou une marque : si tu ne trouves pas, sur le site d'une de ces enseignes
elles-mêmes, de fiche produit pour un parfum respectant ces critères, ne le propose pas.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, dans ce format exact :
{{
  "matches": [
    {{
      "brand": "nom de la marque",
      "name": "nom du parfum",
      "reason": "explication courte (1-2 phrases) en {lang_name} de la ressemblance olfactive",
      "source_url": "URL de la source"
    }}
  ]
}}

Propose {_CANDIDATE_COUNT} parfums candidats de MARQUES TOUTES DIFFÉRENTES (jamais deux parfums de
la même marque), classés du plus au moins proche de la formule — ce nombre volontairement supérieur
à {_COUNT} laisse une marge si certaines de tes sources ne respectent finalement pas les critères
ci-dessus."""

    site_filters = " OR ".join(f"site:{d}" for d in _ALLOWED_RETAILER_DOMAINS)
    user_input = f"""Formule à comparer :
{f"Profil : {profile}" if profile else ""}
{notes_text}

Trouve {_CANDIDATE_COUNT} parfums qui ressemblent le plus à cette composition, en effectuant tes
recherches web directement sur les sites suivants (utilise des requêtes de la forme
"{site_filters}" combinées à des mots-clés olfactifs, ou visite directement leurs rayons
parfums femme/homme) : {", ".join(_ALLOWED_RETAILER_DOMAINS)}.
Ne cherche PAS sur des sites d'avis/encyclopédies de parfums (Fragrantica, etc.) ni sur des
boutiques de marques niche — trouve directement la fiche produit sur un des sites listés
ci-dessus."""

    client = AsyncOpenAI(api_key=get_settings().openai_api_key)

    # 1er appel : recherche web libre. Avec l'outil web_search activé, le modèle ne respecte
    # pas de façon fiable une consigne "réponds en JSON" (il répond en texte narratif avec
    # citations de liens) — on le laisse donc répondre librement ici.
    try:
        search_response = await client.responses.create(
            model=_MODEL,
            tools=[{"type": "web_search"}],
            instructions=instructions,
            input=user_input,
        )
    except Exception:
        logger.exception("[similar_perfumes] échec de l'appel LLM/web_search")
        return {"error": "Impossible de rechercher des parfums similaires pour le moment"}

    search_text = search_response.output_text
    if not search_text:
        return {"error": "Aucun parfum similaire trouvé"}

    # 2e appel : reformatage strict en JSON (sans outil, donc json_object fiable) à partir
    # du texte de recherche produit ci-dessus — aucune nouvelle information n'est ajoutée.
    try:
        format_response = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""Tu reformates un texte de résultats de recherche en JSON structuré.
N'invente aucune information : extrais uniquement ce qui est présent dans le texte fourni.

Réponds UNIQUEMENT avec un objet JSON valide dans ce format exact :
{{
  "matches": [
    {{
      "brand": "nom de la marque",
      "name": "nom du parfum",
      "reason": "explication courte (1-2 phrases) en {lang_name} de la ressemblance olfactive",
      "source_url": "URL de la source"
    }}
  ]
}}""",
                },
                {"role": "user", "content": search_text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception:
        logger.exception("[similar_perfumes] échec du reformatage JSON")
        return {"error": "Impossible de rechercher des parfums similaires pour le moment"}

    matches = _parse_matches(format_response.choices[0].message.content)
    if not matches:
        return {"error": "Aucun parfum similaire trouvé"}

    return {"similar_perfumes": matches}


def _extract_json_object(text: str) -> str | None:
    """Le modèle respecte parfois mal la consigne 'JSON only' quand web_search est actif
    (ajoute une phrase d'intro, un bloc ```json, etc.) — on extrait le premier objet {...}
    équilibré plutôt que de supposer que toute la réponse est du JSON pur."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _parse_matches(raw_text: str) -> list[dict]:
    json_text = _extract_json_object(raw_text or "")
    if json_text is None:
        logger.warning("[similar_perfumes] réponse LLM sans objet JSON : %.200s", raw_text)
        return []
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        logger.warning("[similar_perfumes] objet JSON extrait invalide : %.200s", json_text)
        return []

    matches = []
    seen_brands: set[str] = set()
    for m in parsed.get("matches", []):
        if len(matches) >= _COUNT:
            break
        brand = (m.get("brand") or "").strip()
        name = (m.get("name") or "").strip()
        source_url = (m.get("source_url") or "").strip()
        if not brand or not name or not source_url:
            continue
        if not _is_allowed_source(source_url):
            logger.info("[similar_perfumes] rejeté (source hors enseignes autorisées) : %s — %s", name, source_url)
            continue
        if brand.lower() in seen_brands:
            continue
        seen_brands.add(brand.lower())
        matches.append({
            "brand": brand,
            "name": name,
            "reason": (m.get("reason") or "").strip(),
            "source_url": source_url,
        })
    return matches
