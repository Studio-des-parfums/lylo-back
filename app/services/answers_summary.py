"""Résumé des réponses au questionnaire pour les prompts de génération (formules, catalogue).

Chaque réponse porte son cadrage (`framing`, cf. app/core/answer_format.py) :
  preference : choix préférés / moins appréciés (goûts directs)
  trait      : ce qui représente le plus / le moins la personne (personnalité)
"""
import json

TRAIT_GUIDANCE = (
    "Certaines réponses décrivent la PERSONNALITÉ du client (ce qui le représente le plus / le moins), "
    "pas ses goûts olfactifs directs : traduis ces traits en choix olfactifs cohérents (caractère, "
    "énergie, chaleur, intensité des notes) plutôt que de chercher un lien littéral avec les mots."
)


def _answer_lines(qid: str, data) -> str:
    if isinstance(data, str):
        data = json.loads(data)
    q = data.get("question", f"Question {qid}")
    top = ", ".join(data.get("top_2", []))
    bottom = ", ".join(data.get("bottom_2", []))
    if data.get("framing") == "trait":
        lines = f"- {q}\n  Le/la représente le plus: {top}"
        return lines + (f"\n  Le/la représente le moins: {bottom}" if bottom else "")
    lines = f"- {q}\n  Préférées: {top}"
    return lines + (f"\n  Moins appréciées: {bottom}" if bottom else "")


def summarize_answers(answers: dict) -> str:
    """Bloc texte des réponses (+ consigne de traduction si des réponses sont des traits)."""
    blocks = [_answer_lines(qid, data) for qid, data in answers.items()]
    has_traits = any(
        (json.loads(d) if isinstance(d, str) else d).get("framing") == "trait" for d in answers.values()
    )
    summary = "\n".join(blocks)
    return f"{summary}\n\n{TRAIT_GUIDANCE}" if has_traits else summary
