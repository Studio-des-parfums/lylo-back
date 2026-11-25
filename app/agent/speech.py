"""Adaptation du texte avant synthèse vocale.

Les libellés de choix contiennent des formes inclusives (« solo/a », « Rodeado/a »,
« seul(e) ») que le TTS lit littéralement. On les remplace par la forme qui correspond au
genre de l'utilisateur (masculin par défaut si inconnu).
"""
import re

_GENDER_FORM = re.compile(r"\b(\w+)(?:/(\w{1,2})\b|\((\w{1,2})\))")
_GENDER_SUFFIXES = {"a", "e", "as", "es"}
_FEMININE = {"féminin", "feminin", "female", "f", "femenino", "femenina", "weiblich", "женский", "أنثى"}


def is_feminine(gender: str | None) -> bool:
    return (gender or "").strip().lower() in _FEMININE


def _gendered(match: re.Match, feminine: bool) -> str:
    word, suffix = match.group(1), match.group(2) or match.group(3)
    if suffix.lower() not in _GENDER_SUFFIXES:
        return match.group(0)  # « et/ou », « km/h »… : inchangé
    if not feminine:
        return word
    # solo/a → sola, todos/as → todas ; seul(e) → seule, prêt/e → prête
    if len(suffix) == 1 and word[-1].lower() in "aeiou" and word[-1].lower() != suffix.lower():
        return word[:-1] + suffix
    if len(suffix) == 2 and word[-2:].lower() in ("os", "es") and word[-2:].lower() != suffix.lower():
        return word[:-2] + suffix
    return word + suffix


def resolve_gender_forms(text: str, feminine: bool) -> str:
    return _GENDER_FORM.sub(lambda m: _gendered(m, feminine), text)
