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


# ── Résolution des réponses vers les libellés exacts ─────────────────────────

_NUMBER_WORDS = {
    "un": 1, "une": 1, "premier": 1, "premiere": 1, "one": 1, "first": 1,
    "deux": 2, "deuxieme": 2, "second": 2, "seconde": 2, "two": 2,
    "trois": 3, "troisieme": 3, "three": 3, "third": 3,
    "quatre": 4, "quatrieme": 4, "four": 4, "fourth": 4,
    "cinq": 5, "cinquieme": 5, "five": 5, "fifth": 5,
    "six": 6, "sixieme": 6, "sixth": 6,
}


def _normalize(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def resolve_choices(values: list, labels: list[str]) -> list[str]:
    """Ramène chaque réponse (numéro « 4 », « le choix numéro 4 », libellé approximatif)
    au libellé exact du choix, pour que le front puisse masquer/afficher les bonnes cartes.
    Une valeur introuvable est conservée telle quelle ; les doublons sont retirés."""
    import difflib
    import re

    norm_labels = [_normalize(l) for l in labels]
    out: list[str] = []
    for raw in values:
        text = _normalize(str(raw))
        label = None
        if text in norm_labels:
            label = labels[norm_labels.index(text)]
        else:
            m = re.fullmatch(r"(?:(?:le|la|choix|numero|number|n°|no|#)\s*)*(\d+|[a-z]+)\.?", text)
            n = None
            if m:
                tok = m.group(1)
                n = int(tok) if tok.isdigit() else _NUMBER_WORDS.get(tok)
            if n is not None and 1 <= n <= len(labels):
                label = labels[n - 1]
            else:
                close = difflib.get_close_matches(text, norm_labels, n=1, cutoff=0.5)
                label = labels[norm_labels.index(close[0])] if close else str(raw)
        if label not in out:
            out.append(label)
    return out
