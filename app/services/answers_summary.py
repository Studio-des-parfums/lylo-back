"""Résumé des réponses au questionnaire pour les prompts de génération (formules, catalogue).

Chaque réponse porte les libellés de son questionnaire (« Vos préférés »,
« Ce qui vous représente le plus »…) : le LLM comprend seul s'il s'agit de goûts ou de
traits de personnalité, sans cas particulier dans le code.
"""
import json


def _answer_lines(qid: str, data) -> str:
    if isinstance(data, str):
        data = json.loads(data)
    q = data.get("question", f"Question {qid}")
    top = ", ".join(data.get("top_2", []))
    bottom = ", ".join(data.get("bottom_2", []))
    lines = f"- {q}\n  {data.get('positive_label') or 'Préférées'}: {top}"
    return lines + (f"\n  {data.get('negative_label') or 'Moins appréciées'}: {bottom}" if bottom else "")


def summarize_answers(answers: dict) -> str:
    return "\n".join(_answer_lines(qid, data) for qid, data in answers.items())
