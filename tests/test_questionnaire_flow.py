"""Enchaînement des étapes d'une question selon le format de réponse."""
from app.agent import questionnaire_flow as flow
from app.agent.state import AgentPhase as P, SessionState
from app.core.answer_format import AnswerFormat


def run(fmt: AnswerFormat, top: list[str], bottom: list[str]) -> list[P]:
    """Simule une question complète (le LLM appelle les outils dans l'ordre) → phases visitées."""
    state = SessionState(phase=P.Q_FAVORITES)
    visited = [state.phase]

    def go(phase: P) -> None:
        state.phase = phase
        visited.append(phase)

    state.current_top_2 = top
    go(flow.after_positive_choices(fmt, state))
    while state.phase == P.Q_JUSTIFY_POSITIVE:
        go(flow.after_justification(fmt, state))
    if state.phase == P.Q_LEAST:
        state.current_bottom_2 = bottom
        go(flow.after_negative_choices(fmt, state))
        while state.phase == P.Q_JUSTIFY_NEGATIVE:
            go(flow.after_justification(fmt, state))
    return visited


def test_lylo_2_plus_2_justified():
    assert run(AnswerFormat(), ["A", "B"], ["C", "D"]) == [
        P.Q_FAVORITES, P.Q_JUSTIFY_POSITIVE, P.Q_JUSTIFY_POSITIVE,
        P.Q_LEAST, P.Q_JUSTIFY_NEGATIVE, P.Q_JUSTIFY_NEGATIVE, P.Q_CONFIRM,
    ]


def test_help_1_plus_1_justified():
    fmt = AnswerFormat(framing="trait", positive_count=1, negative_count=1)
    assert run(fmt, ["Direct"], ["Indirect"]) == [
        P.Q_FAVORITES, P.Q_JUSTIFY_POSITIVE, P.Q_LEAST, P.Q_JUSTIFY_NEGATIVE, P.Q_CONFIRM,
    ]


def test_no_negative_step():
    fmt = AnswerFormat(positive_count=2, negative_count=0)
    assert run(fmt, ["A", "B"], []) == [
        P.Q_FAVORITES, P.Q_JUSTIFY_POSITIVE, P.Q_JUSTIFY_POSITIVE, P.Q_CONFIRM,
    ]


def test_no_justification():
    fmt = AnswerFormat(positive_justify=False, negative_justify=False)
    assert run(fmt, ["A", "B"], ["C", "D"]) == [P.Q_FAVORITES, P.Q_LEAST, P.Q_CONFIRM]


def test_missing_format_means_historical_format():
    assert flow.answer_format({}) == AnswerFormat()
    assert flow.answer_format({"answer_format": {}}) == AnswerFormat()


def test_labels_resolved_per_language_with_fallbacks():
    from types import SimpleNamespace
    from app.core.answer_format import answer_format_of

    group = SimpleNamespace(
        positive_label={"fr": "Me représente le plus", "en": "Describes me best"}, negative_label=None,
        positive_count=1, positive_justify=True, negative_count=1, negative_justify=True,
    )
    assert answer_format_of(group, "en")["positive_label"] == "Describes me best"
    assert answer_format_of(group, "de")["positive_label"] == "Me représente le plus"  # repli fr
    assert answer_format_of(group, "en")["negative_label"] == "Your least favorites"   # défaut
