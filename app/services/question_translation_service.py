"""Traduction automatique des questions/choix du questionnaire depuis le français.

L'admin (sdp-dashboard) ne saisit le contenu du questionnaire qu'en français — ce service
traduit le texte d'une question (et, séparément, le texte d'un choix) vers toutes les autres
langues supportées, pour que les questions traduites soient créées automatiquement côté
catalogue (voir app/database/crud.py: create_question_with_translations / create_choice_with_translations).
"""

import json
import logging

from openai import AsyncOpenAI

from app.config import get_settings
from app.core.languages import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, SupportedLanguage

logger = logging.getLogger("lylo.question_translation")

_MODEL = "gpt-4o-mini"

# Langues vers lesquelles on traduit automatiquement depuis le français.
TARGET_LANGUAGES: list[SupportedLanguage] = [lang for lang in SUPPORTED_LANGUAGES if lang != "fr"]


async def translate_text(text: str) -> dict[SupportedLanguage, str]:
    """Traduit un texte court (question ou choix) depuis le français vers toutes les
    TARGET_LANGUAGES en un seul appel LLM. Retourne {langue: texte traduit}, avec un
    repli sur le texte original pour toute langue absente de la réponse (jamais d'erreur
    bloquante — mieux vaut un texte non traduit qu'une question manquante)."""
    results = await _translate_texts([text])
    return results[0]


async def translate_texts(texts: list[str]) -> list[dict[SupportedLanguage, str]]:
    """Variante batch de translate_text — un seul appel LLM pour plusieurs textes
    (ex: la question + tous ses choix), pour limiter la latence/coût."""
    return await _translate_texts(texts)


async def _translate_texts(texts: list[str]) -> list[dict[SupportedLanguage, str]]:
    if not texts:
        return []

    lang_labels = {lang: LANGUAGE_NAMES[lang] for lang in TARGET_LANGUAGES}
    numbered_texts = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))

    system_prompt = f"""Tu traduis des textes courts d'un questionnaire de parfumerie depuis le français.
Traduis chaque texte numéroté vers les langues suivantes : {", ".join(f"{code} ({label})" for code, label in lang_labels.items())}.
Garde un ton et une longueur similaires à l'original. Ne traduis pas littéralement au mot à
mot si une formulation plus naturelle existe dans la langue cible.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, dans ce format exact :
{{
  "translations": [
    {{"index": 0, {", ".join(f'"{code}": "texte traduit"' for code in lang_labels)}}}
  ]
}}

Un objet par texte numéroté, dans le même ordre."""

    client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": numbered_texts},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        parsed = json.loads(response.choices[0].message.content)
    except Exception:
        logger.exception("[question_translation] échec de la traduction — repli sur le texte original")
        return [{lang: text for lang in TARGET_LANGUAGES} for text in texts]

    raw_translations = parsed.get("translations", [])
    by_index = {}
    for item in raw_translations:
        idx = item.get("index")
        if isinstance(idx, int):
            by_index[idx] = item

    results = []
    for i, original_text in enumerate(texts):
        item = by_index.get(i, {})
        results.append({
            lang: (item.get(lang) or "").strip() or original_text
            for lang in TARGET_LANGUAGES
        })
    return results
