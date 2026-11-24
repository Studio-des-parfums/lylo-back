"""Format de réponse d'un questionnaire (porté par question_groups, réglé dans le dashboard).

Pilote la machine à états de l'agent, le quiz du front et le résumé envoyé au générateur.
Les libellés (« Vos préférés », « Ce qui vous représente le plus »…) sont des données
traduites, pas du code : n'importe quelle formulation sans toucher aux prompts.
Valeurs par défaut = format historique Lylo : 2 favoris + 2 moins aimés, tous justifiés.
"""
from pydantic import BaseModel, Field

from app.core.languages import SupportedLanguage

LabelTranslations = dict[str, str]  # {langue: libellé}

DEFAULT_POSITIVE_LABEL: dict[SupportedLanguage, str] = {
    "fr": "Vos préférés", "en": "Your favorites", "es": "Sus favoritos",
    "de": "Ihre Favoriten", "ar": "مفضلاتك", "ru": "Ваши любимые",
}
DEFAULT_NEGATIVE_LABEL: dict[SupportedLanguage, str] = {
    "fr": "Les moins aimés", "en": "Your least favorites", "es": "Los que menos le gustan",
    "de": "Am wenigsten gemocht", "ar": "الأقل تفضيلاً", "ru": "Наименее любимые",
}


class AnswerFormat(BaseModel):
    """Format résolu pour une langue (envoyé au front et à l'agent)."""
    positive_label: str = DEFAULT_POSITIVE_LABEL["fr"]
    negative_label: str = DEFAULT_NEGATIVE_LABEL["fr"]
    positive_count: int = Field(2, ge=1, le=3)
    positive_justify: bool = True
    negative_count: int = Field(2, ge=0, le=3)  # 0 = pas d'étape « le moins »
    negative_justify: bool = True


def resolve_label(labels: LabelTranslations | None, defaults: dict, language: str) -> str:
    labels = labels or {}
    return labels.get(language) or labels.get("fr") or defaults.get(language) or defaults["fr"]


def answer_format_of(group, language: str) -> dict:
    """AnswerFormat (dict) d'un QuestionGroup SQLAlchemy, libellés dans la langue demandée."""
    return AnswerFormat(
        positive_label=resolve_label(group.positive_label, DEFAULT_POSITIVE_LABEL, language),
        negative_label=resolve_label(group.negative_label, DEFAULT_NEGATIVE_LABEL, language),
        positive_count=group.positive_count,
        positive_justify=group.positive_justify,
        negative_count=group.negative_count,
        negative_justify=group.negative_justify,
    ).model_dump()
