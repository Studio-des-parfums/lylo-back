"""Profil de marque : ce qui distingue le comportement de l'IA d'une marque à l'autre.

Une marque assemble des briques communes (sécurité, format de questionnaire, moteur de
résultat, veille) et ne surcharge que ce qui diffère. Pour une nouvelle marque : hériter
de LyloProfile, surcharger `missions` / `personality`, puis l'enregistrer dans registry.py.
"""
from collections.abc import Callable
from typing import ClassVar, Literal

from app.agent.prompts import questionnaire, result_formula, safety, standby
from app.agent.prompts.context import PromptContext
from app.agent.prompts.personality import PERSONALITY
from app.agent.state import AgentPhase

Mission = Callable[[PromptContext], str]
ResultEngine = Literal["formula", "catalog"]


class BrandProfile:
    slug: ClassVar[str]
    # "formula" : génère des formules à partir du catalogue de notes (formula_service)
    # "catalog" : recommande des parfums existants du catalogue (catalog_service)
    result_engine: ClassVar[ResultEngine] = "formula"
    missions: ClassVar[dict[AgentPhase, Mission]] = {
        **safety.MISSIONS,
        **questionnaire.MISSIONS,
        **result_formula.MISSIONS,
        **standby.MISSIONS,
    }

    def personality(self, ctx: PromptContext) -> str:
        return PERSONALITY.get(ctx.lang, PERSONALITY["fr"]).format(ai_name=ctx.ai_name)

    def mission(self, ctx: PromptContext) -> str | None:
        build = self.missions.get(ctx.state.phase)
        return build(ctx) if build else None
