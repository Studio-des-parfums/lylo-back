"""Prompt système de l'agent : personnalité de la marque + mission de la phase courante."""
from app.agent.brands.registry import get_brand_profile
from app.agent.i18n import t
from app.agent.prompts.context import PromptContext
from app.agent.state import SessionState
from app.core.languages import SupportedLanguage


def get_prompt(state: SessionState, config: dict, ai_name: str, lang: SupportedLanguage, input_mode: str) -> str:
    profile = get_brand_profile(config.get("brand"))
    ctx = PromptContext(state=state, config=config, ai_name=ai_name, lang=lang, input_mode=input_mode)
    mission = profile.mission(ctx) or t("continue_naturally", lang)
    return f"{profile.personality(ctx)}\n\n--- MISSION ACTUELLE ---\n\n{mission}"
