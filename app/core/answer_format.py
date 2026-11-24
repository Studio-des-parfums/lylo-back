"""Format de réponse d'un questionnaire (porté par question_groups, réglé dans le dashboard).

Pilote la machine à états de l'agent, le quiz du front et le résumé envoyé au générateur.
Valeurs par défaut = format historique Lylo : 2 favoris + 2 moins aimés, tous justifiés.
"""
from typing import Literal

from pydantic import BaseModel, Field

Framing = Literal["preference", "trait"]


class AnswerFormat(BaseModel):
    # "preference" : choix aimés / moins aimés ; "trait" : « vous êtes plutôt… » (le plus / le moins)
    framing: Framing = "preference"
    positive_count: int = Field(2, ge=1, le=3)
    positive_justify: bool = True
    negative_count: int = Field(2, ge=0, le=3)  # 0 = pas d'étape « moins aimé »
    negative_justify: bool = True


def answer_format_of(group) -> dict:
    """AnswerFormat (dict) d'un QuestionGroup SQLAlchemy."""
    return AnswerFormat(
        framing=group.framing,
        positive_count=group.positive_count,
        positive_justify=group.positive_justify,
        negative_count=group.negative_count,
        negative_justify=group.negative_justify,
    ).model_dump()
