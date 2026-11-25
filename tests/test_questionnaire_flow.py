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


def test_resolve_choices_numbers_and_fuzzy():
    from app.agent.questionnaire_flow import resolve_choices
    labels = ["Vous êtes d'une efficacité redoutable", "Vous avez des idées que personne n'a",
              "On peut toujours compter sur vous", "Vous êtes toujours calme"]
    assert resolve_choices(["4"], labels) == [labels[3]]
    assert resolve_choices(["le choix numéro 2"], labels) == [labels[1]]
    assert resolve_choices(["le quatre"], labels) == [labels[3]]
    assert resolve_choices(["Vous savez des idées que personne n'a"], labels) == [labels[1]]
    assert resolve_choices(["on peut toujours compter sur vous"], labels) == [labels[2]]


def test_count_mismatch():
    from app.agent.questionnaire_flow import count_mismatch
    assert count_mismatch(["A"], 1, "le plus") is None
    assert count_mismatch(["A", "B"], 2, "le plus") is None
    msg = count_mismatch(["A", "B"], 1, "Ce qui vous représente le plus")
    assert msg and msg.startswith("[rejected]") and "ONE choice" in msg
    assert count_mismatch(["A"], 2, "x").startswith("[rejected]")


HELP_LABELS = ["Lance les idées", "Construit le plan", "Fédère l'équipe", "Anticipe les risques"]


def test_resolve_numbered_label_uses_card_number():
    # Libellé inventé par le LLM mais préfixé du numéro de carte : le numéro fait foi
    assert flow.resolve_choices(["1. Je fonce, tête baissée"], HELP_LABELS) == ["Lance les idées"]
    assert flow.resolve_choices(["3) Je suis plus en retrait"], HELP_LABELS) == ["Fédère l'équipe"]


def test_unknown_choices_rejected():
    resolved = flow.resolve_choices(["Je fonce, tête baissée"], HELP_LABELS)
    msg = flow.unknown_choices(resolved, HELP_LABELS)
    assert msg and msg.startswith("[rejected]") and "1. Lance les idées" in msg
    assert flow.unknown_choices(["Construit le plan"], HELP_LABELS) is None


def test_change_of_favorite_at_recap_skips_least_step():
    fmt = AnswerFormat(positive_count=1, negative_count=1)
    state = SessionState(phase=P.Q_JUSTIFY_POSITIVE, current_top_2=["B"], current_bottom_2=["C"])
    # « le moins » déjà donné : après la justification du nouveau choix, retour au récap
    assert flow.after_justification(fmt, state) == P.Q_CONFIRM
    state = SessionState(phase=P.Q_JUSTIFY_POSITIVE, current_top_2=["B"], current_bottom_2=[])
    assert flow.after_justification(fmt, state) == P.Q_LEAST
