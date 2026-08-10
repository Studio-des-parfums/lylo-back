"""Service de matching catalogue pour la marque Esther.

Contrairement à Lylo (formula_service.py), qui invente une formule de parfum
sur-mesure à partir d'ingrédients, Esther sélectionne 2-3 parfums *existants*
dans un catalogue statique (fichier Excel) via un LLM qui choisit parmi ce
catalogue, sans jamais inventer de notes.
"""

import json
import logging
from pathlib import Path

import openpyxl
from openai import AsyncOpenAI

from app.config import get_settings
from app.services import session_store

logger = logging.getLogger("lylo.catalog")

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "ELC_Guide_de_Reformulation_Parfums_FR.xlsx"
_SHEET_NAME = "Pyramides Olfactives"
_EXCLUDED_BRANDS = {"BALMAIN Beauty"}  # gamme "en développement", pas de vrais parfums
_LEGEND_BRAND_PREFIX = "légende"  # ligne de légende en fin de feuille ("Légende : Tête | Cœur | Fond")

_catalog_cache: list[dict] | None = None


# ── Chargement du catalogue depuis l'Excel ─────────────────────────────

def _load_catalog_from_excel() -> list[dict]:
    """Lit le fichier Excel une seule fois par process et normalise les lignes.

    La colonne 'Marque' n'est renseignée que sur la 1re ligne de chaque
    groupe de parfums (fusion visuelle dans le fichier) — forward-fill
    nécessaire via `current_brand`.
    """
    wb = openpyxl.load_workbook(_CATALOG_PATH, data_only=True)
    ws = wb[_SHEET_NAME]

    perfumes: list[dict] = []
    current_brand: str | None = None

    for row in ws.iter_rows(min_row=5, values_only=True):
        brand_cell, name = row[0], row[1]
        if brand_cell:
            current_brand = str(brand_cell).strip()
        if not name or not current_brand:
            continue
        if current_brand.lower().startswith(_LEGEND_BRAND_PREFIX):
            continue
        if current_brand in _EXCLUDED_BRANDS:
            continue

        perfumes.append({
            "brand": current_brand,
            "name": str(name).strip(),
            "type": (row[2] or "").strip() if row[2] else "",
            "family": (row[3] or "").strip() if row[3] else "",
            "top_notes": (row[4] or "").strip() if row[4] else "",
            "top_materials": (row[5] or "").strip() if row[5] else "",
            "heart_notes": (row[6] or "").strip() if row[6] else "",
            "heart_materials": (row[7] or "").strip() if row[7] else "",
            "base_notes": (row[8] or "").strip() if row[8] else "",
            "base_materials": (row[9] or "").strip() if row[9] else "",
            "image_url": (row[11] or "").strip() if len(row) > 11 and row[11] else "",
        })

    logger.info("[catalog] %d parfums chargés depuis %s", len(perfumes), _CATALOG_PATH.name)
    return perfumes


def get_catalog() -> list[dict]:
    """Retourne le catalogue en cache (chargé une seule fois par process)."""
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = _load_catalog_from_excel()
    return _catalog_cache


def _split_notes(notes: str) -> list[str]:
    return [n.strip() for n in notes.split(",") if n.strip()]


# ── Appel LLM ────────────────────────────────────────────────────────

async def _ask_llm_for_matches(
    answers: dict,
    catalog: list[dict],
    user_allergens: list[str] | None,
    language: str,
    count: int,
) -> list[dict]:
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)

    answers_summary = []
    for qid, data in answers.items():
        if isinstance(data, str):
            data = json.loads(data)
        q = data.get("question", f"Question {qid}")
        top = ", ".join(data.get("top_2", []))
        bottom = ", ".join(data.get("bottom_2", []))
        answers_summary.append(f"- {q}\n  Préférées: {top}\n  Moins appréciées: {bottom}")

    catalog_lines = []
    for i, p in enumerate(catalog):
        catalog_lines.append(
            f"[{i}] {p['brand']} — {p['name']} ({p['family']})\n"
            f"    Tête: {p['top_notes']} | Cœur: {p['heart_notes']} | Fond: {p['base_notes']}"
        )
    catalog_text = "\n".join(catalog_lines)

    allergen_instruction = (
        f"Le client a déclaré les allergies suivantes : {', '.join(user_allergens)}. "
        "Exclue tout parfum du catalogue dont les notes correspondent clairement à ces allergènes."
        if user_allergens else "Le client n'a pas déclaré d'allergies."
    )

    system_prompt = f"""Tu es un expert en parfumerie de luxe. Tu dois choisir, PARMI le catalogue fourni
ci-dessous (et UNIQUEMENT parmi celui-ci, sans en inventer), les {count} parfums qui
correspondent le mieux aux préférences olfactives exprimées par le client dans son questionnaire.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, dans ce format exact :
{{
  "matches": [
    {{
      "catalog_index": 0,
      "match_reason": "description courte et poétique en {'français' if language == 'fr' else 'anglais'} expliquant pourquoi ce parfum correspond au profil du client (2-3 phrases)"
    }}
  ]
}}

"catalog_index" DOIT être l'index exact entre crochets [n] du parfum choisi dans la liste fournie.
Choisis exactement {count} parfums, tous DIFFÉRENTS, en variant les marques si possible."""

    user_prompt = f"""Réponses du client au questionnaire :
{chr(10).join(answers_summary)}

{allergen_instruction}

Catalogue disponible :
{catalog_text}

Sélectionne les {count} parfums les plus cohérents avec les préférences du client."""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    llm_result = json.loads(response.choices[0].message.content)
    return _normalize_matches(llm_result.get("matches", []), catalog, count)


def _normalize_matches(raw_matches: list[dict], catalog: list[dict], count: int) -> list[dict]:
    """Valide les index renvoyés par le LLM contre le catalogue réel — ne jamais
    faire confiance aveuglément à un LLM pour des indices numériques."""
    selected: list[dict] = []
    seen_indices: set[int] = set()

    for m in raw_matches:
        idx = m.get("catalog_index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(catalog) or idx in seen_indices:
            continue
        entry = _to_result_entry(catalog[idx], m.get("match_reason", ""))
        selected.append(entry)
        seen_indices.add(idx)
        if len(selected) == count:
            return selected

    # Filet de sécurité : compléter avec les premiers parfums non utilisés
    # si le LLM a renvoyé moins que `count` résultats valides.
    for i, p in enumerate(catalog):
        if i in seen_indices:
            continue
        selected.append(_to_result_entry(p, ""))
        seen_indices.add(i)
        if len(selected) == count:
            break

    return selected


def _to_result_entry(perfume: dict, match_reason: str) -> dict:
    return {
        "source": "catalog",
        "brand": perfume["brand"],
        "name": perfume["name"],
        "type": perfume["type"],
        "family": perfume["family"],
        "top_notes": _split_notes(perfume["top_notes"]),
        "heart_notes": _split_notes(perfume["heart_notes"]),
        "base_notes": _split_notes(perfume["base_notes"]),
        "match_reason": match_reason,
        "image_url": perfume.get("image_url", ""),
    }


# ── API principale (miroir de formula_service) ─────────────────────────

async def match_perfumes(session_id: str, count: int = 3) -> dict:
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

    catalog = get_catalog()
    if not catalog:
        return {"error": "Catalogue indisponible", "formulas": []}

    matches = await _ask_llm_for_matches(session_data["answers"], catalog, user_allergens, language, count)

    session_store.save_generated_formulas(session_id, matches)
    return {"formulas": matches}


async def match_perfumes_stateless(
    answers: dict,
    language: str = "fr",
    has_allergies: str = "non",
    user_allergens_raw: str = "",
    count: int = 3,
) -> dict:
    if not answers:
        return {"error": "Aucune réponse fournie", "formulas": []}

    user_allergens = None
    if has_allergies in ("oui", "yes") and user_allergens_raw:
        user_allergens = [a.strip() for a in user_allergens_raw.replace(",", ";").split(";") if a.strip()]

    catalog = get_catalog()
    if not catalog:
        return {"error": "Catalogue indisponible", "formulas": []}

    matches = await _ask_llm_for_matches(answers, catalog, user_allergens, language, count)
    return {"formulas": matches}


def select_match(session_id: str, formula_index: int) -> dict:
    matches = session_store.get_generated_formulas(session_id)
    if not matches:
        return {"error": "No catalog matches found"}
    if formula_index < 0 or formula_index >= len(matches):
        return {"error": f"formula_index must be between 0 and {len(matches) - 1}"}
    selected = matches[formula_index]
    session_store.save_selected_formula(session_id, selected)
    return {"formula": selected}
