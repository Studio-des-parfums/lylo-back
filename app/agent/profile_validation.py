"""Validation des réponses du profil (étapes obligatoires, pilotées par le code).

Prénom, genre, âge, grossesse, notes détestées et allergies sont OBLIGATOIRES : le genre
et l'âge changent complètement la recommandation, les autres sont des questions de
sécurité. Le LLM ne peut enregistrer qu'une valeur valide pour l'étape en cours — sinon
l'outil refuse et l'agent doit reposer la question, jamais passer à la suite.
"""
import re
import unicodedata

from app.agent.state import AgentPhase

# Champ attendu à chaque étape du profil
EXPECTED_FIELD = {
    AgentPhase.GREET: "first_name",
    AgentPhase.GET_GENDER: "gender",
    AgentPhase.GET_AGE: "age",
    AgentPhase.GET_PREGNANT: "pregnant",
    AgentPhase.GET_DISLIKES: "has_disliked_notes",
    AgentPhase.GET_DISLIKE_DETAIL: "disliked_notes",
    AgentPhase.GET_ALLERGIES: "has_allergies",
    AgentPhase.GET_ALLERGY_DETAIL: "allergies",
}

_MASCULINE = {"masculin", "homme", "male", "man", "masculine", "m", "hombre", "masculino", "mann", "mannlich",
              "мужской", "мужчина", "ذكر", "رجل", "مذكر"}
_FEMININE = {"feminin", "femme", "female", "woman", "feminine", "f", "mujer", "femenino", "femenina", "frau",
             "weiblich", "женский", "женщина", "أنثى", "امرأة", "مؤنث"}
_YES = {"oui", "yes", "si", "ja", "да", "نعم"}
_NO = {"non", "no", "nein", "нет", "لا"}

_GENDER_REFUSAL = (
    "[rejected] Gender is REQUIRED and must be masculine or feminine: the perfume recommendation (notes, "
    "formula) is completely different depending on it. Nothing was recorded. Do NOT move on to another step. "
    "Kindly explain this in one sentence, in the user's language, and ask again whether you should base the "
    "formula on a masculine or a feminine profile."
)


def _norm(value: str) -> str:
    v = unicodedata.normalize("NFD", str(value))
    return "".join(c for c in v if unicodedata.category(c) != "Mn").lower().strip(" .!?,;")


def _required(what: str) -> str:
    return (f"[rejected] {what} Nothing was recorded. This step is REQUIRED: do NOT move on. "
            "Briefly ask the same question again, in the user's language.")


def _yes_no(value: str) -> str | None:
    words = set(re.findall(r"\w+", _norm(value)))
    if words & _YES and not words & _NO:
        return "oui"
    if words & _NO and not words & _YES:
        return "non"
    return None


def validate(field: str, value: str) -> tuple[str | None, str | None]:
    """(valeur normalisée, None) si valide, sinon (None, message de refus pour le LLM)."""
    raw = str(value or "").strip()
    if field == "first_name":
        if not raw or len(raw) > 40 or len(raw.split()) > 3:
            return None, _required("This does not look like a first name.")
        return raw, None
    if field == "gender":
        words = set(re.findall(r"\w+", _norm(raw)))
        is_m, is_f = bool(words & _MASCULINE), bool(words & _FEMININE)
        if is_m == is_f:  # ni l'un ni l'autre, ou les deux
            return None, _GENDER_REFUSAL
        return ("masculin" if is_m else "féminin"), None
    if field == "age":
        m = re.search(r"\d+", raw)
        if not m or not 12 <= int(m.group()) <= 120:
            return None, _required("The age must be a number between 12 and 120.")
        return m.group(), None
    if field in ("pregnant", "has_disliked_notes", "has_allergies"):
        yn = _yes_no(raw)
        if yn is None:
            return None, _required("The answer must be yes or no.")
        return yn, None
    if field in ("disliked_notes", "allergies"):
        if not raw:
            return None, _required("The details are missing.")
        return raw, None
    return raw, None
