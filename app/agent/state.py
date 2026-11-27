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
    # Enchaînement selon le format de réponse : voir app/agent/questionnaire_flow.py
    Q_FAVORITES = auto()          # choix « le plus » (favoris / me représente le plus)
    Q_JUSTIFY_POSITIVE = auto()   # justification de current_top_2[justify_index]
    Q_LEAST = auto()              # choix « le moins »
    Q_JUSTIFY_NEGATIVE = auto()   # justification de current_bottom_2[justify_index]
    Q_CONFIRM = auto()
    # Phase 3 — Formules
    INTENSITY = auto()
    PERFUME_NAME = auto()
    PRESENT_FORMULAS = auto()
    # Phase 4 — Personnalisation / Découverte
    CUSTOMIZATION = auto()
    # Accompagnement physique jusqu'au lieu annoncé par le client (voir prompts/guide.py)
    GUIDING = auto()
    # Phase 5 — Fin
    STANDBY = auto()


@dataclass
class SessionState:
    phase: AgentPhase = AgentPhase.GREET
    current_question_index: int = 0
    current_top_2: list = field(default_factory=list)
    current_bottom_2: list = field(default_factory=list)
    justify_index: int = 0  # choix en cours de justification (Q_JUSTIFY_*)
    profile: dict = field(default_factory=dict)
    answers_saved: int = 0
    formula_type: str | None = None
    perfume_name: str | None = None
    selected_formula_index: int | None = None
    # Accompagnement : None (pas encore) | "moving" | "arrived" | "failed"
    guide_status: str | None = None
    guide_error: str | None = None
