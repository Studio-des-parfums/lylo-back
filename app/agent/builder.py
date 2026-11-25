"""Prompt système de l'agent : personnalité de la marque + mission de la phase courante."""
from app.agent.brands.registry import get_brand_profile
from app.agent.i18n import t
from app.agent.prompts.context import PromptContext
from app.agent.state import AgentPhase, SessionState
from app.core.languages import SupportedLanguage


def get_prompt(state: SessionState, config: dict, ai_name: str, lang: SupportedLanguage, input_mode: str) -> str:
    profile = get_brand_profile(config.get("brand"))
    ctx = PromptContext(state=state, config=config, ai_name=ai_name, lang=lang, input_mode=input_mode)
    mission = profile.mission(ctx) or t("continue_naturally", lang)
    if state.phase in _GUIDED_PHASES:
        mission += _STAY_ON_STEP
    return f"{profile.personality(ctx)}\n\n--- MISSION ACTUELLE ---\n\n{mission}"


# Profil + questionnaire : le parcours est piloté par le code. Sans ce rappel, quand une
# réponse ne rentrait pas dans les cases (genre ni masculin ni féminin), le LLM sortait du
# parcours et improvisait une conversation sur les familles olfactives.
_GUIDED_PHASES = {
    AgentPhase.GREET, AgentPhase.GET_GENDER, AgentPhase.GET_AGE, AgentPhase.GET_PREGNANT,
    AgentPhase.GET_DISLIKES, AgentPhase.GET_DISLIKE_DETAIL, AgentPhase.GET_ALLERGIES,
    AgentPhase.GET_ALLERGY_DETAIL, AgentPhase.Q_FAVORITES, AgentPhase.Q_JUSTIFY_POSITIVE,
    AgentPhase.Q_LEAST, AgentPhase.Q_JUSTIFY_NEGATIVE, AgentPhase.Q_CONFIRM,
}
_STAY_ON_STEP = (
    "\n\nSTAY ON THIS STEP: the journey is driven by the application. Only do what this mission asks. "
    "If the answer is unclear, does not fit or the user refuses, kindly explain why it is needed and ask the "
    "same question again: first name, gender, age, pregnancy, disliked notes and allergies are REQUIRED and "
    "can never be skipped. Never ask about perfume tastes, notes, olfactory families or intensity on your own, "
    "and never skip ahead: the application asks those questions at the right time."
)
