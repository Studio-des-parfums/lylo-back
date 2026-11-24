"""Machine à états de l'agent vocal."""
from dataclasses import dataclass, field
from enum import Enum, auto


class AgentPhase(Enum):
    # Phase 1 — Profil
    GREET = auto()
    GET_GENDER = auto()
    GET_AGE = auto()
    GET_PREGNANT = auto()
    GET_DISLIKES = auto()
    GET_DISLIKE_DETAIL = auto()
    GET_ALLERGIES = auto()
    GET_ALLERGY_DETAIL = auto()
    # Phase 2 — Questionnaire
    Q_FAVORITES = auto()
    Q_JUSTIFY_FAV_1 = auto()
    Q_JUSTIFY_FAV_2 = auto()
    Q_LEAST = auto()
    Q_JUSTIFY_LEAST_1 = auto()
    Q_JUSTIFY_LEAST_2 = auto()
    Q_CONFIRM = auto()
    # Phase 3 — Formules
    INTENSITY = auto()
    PERFUME_NAME = auto()
    PRESENT_FORMULAS = auto()
    # Phase 4 — Personnalisation / Découverte
    CUSTOMIZATION = auto()
    # Phase 5 — Fin
    STANDBY = auto()


@dataclass
class SessionState:
    phase: AgentPhase = AgentPhase.GREET
    current_question_index: int = 0
    current_top_2: list = field(default_factory=list)
    current_bottom_2: list = field(default_factory=list)
    profile: dict = field(default_factory=dict)
    answers_saved: int = 0
    formula_type: str | None = None
    perfume_name: str | None = None
    selected_formula_index: int | None = None
