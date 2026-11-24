"""Données disponibles pour construire le prompt d'une phase."""
from dataclasses import dataclass

from app.agent.state import SessionState
from app.core.languages import SupportedLanguage


@dataclass(frozen=True)
class PromptContext:
    state: SessionState
    config: dict
    ai_name: str
    lang: SupportedLanguage
    input_mode: str

    @property
    def is_en(self) -> bool:
        return self.lang == "en"

    @property
    def questions(self) -> list[dict]:
        return self.config.get("questions", [])

    @property
    def num_questions(self) -> int:
        return len(self.questions)
