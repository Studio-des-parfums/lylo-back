"""Enchaînement des étapes d'une question, piloté par le format de réponse du questionnaire.

    Q_FAVORITES ──► Q_JUSTIFY_POSITIVE × positive_count   (si positive_justify)
                ──► Q_LEAST                               (si negative_count > 0)
                ──► Q_JUSTIFY_NEGATIVE × negative_count   (si negative_justify)
                ──► Q_CONFIRM

C'est le code qui choisit l'étape suivante (pas le prompt) : le LLM signale seulement
« choix donnés » (notify_top_2 / notify_bottom_2) ou « justification reçue »
(justification_done). Fonctions pures, testées dans tests/test_questionnaire_flow.py.
"""
from app.agent.state import AgentPhase, SessionState
from app.core.answer_format import AnswerFormat


def answer_format(config: dict) -> AnswerFormat:
    """Format de la session (meta `answer_format`) ; format historique si absent."""
    return AnswerFormat(**(config.get("answer_format") or {}))


def after_positive_choices(fmt: AnswerFormat, state: SessionState) -> AgentPhase:
    if fmt.positive_justify:
        state.justify_index = 0
        return AgentPhase.Q_JUSTIFY_POSITIVE
    return after_positive_justifications(fmt)


def after_positive_justifications(fmt: AnswerFormat) -> AgentPhase:
    return AgentPhase.Q_LEAST if fmt.negative_count > 0 else AgentPhase.Q_CONFIRM


def after_negative_choices(fmt: AnswerFormat, state: SessionState) -> AgentPhase:
    if fmt.negative_justify:
        state.justify_index = 0
        return AgentPhase.Q_JUSTIFY_NEGATIVE
    return AgentPhase.Q_CONFIRM


def after_justification(fmt: AnswerFormat, state: SessionState) -> AgentPhase:
    """Justification courante reçue : choix suivant du même groupe, sinon étape suivante."""
    if state.phase == AgentPhase.Q_JUSTIFY_POSITIVE:
        if state.justify_index + 1 < len(state.current_top_2):
            state.justify_index += 1
            return AgentPhase.Q_JUSTIFY_POSITIVE
        return after_positive_justifications(fmt)
    if state.phase == AgentPhase.Q_JUSTIFY_NEGATIVE:
        if state.justify_index + 1 < len(state.current_bottom_2):
            state.justify_index += 1
            return AgentPhase.Q_JUSTIFY_NEGATIVE
        return AgentPhase.Q_CONFIRM
    raise ValueError(f"justification_done appelé hors justification (phase={state.phase.name})")
