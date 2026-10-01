from typing import Literal

SupportedLanguage = Literal["fr", "en", "es", "de", "ar", "ru"]

SUPPORTED_LANGUAGES: list[SupportedLanguage] = ["fr", "en", "es", "de", "ar", "ru"]

# Nom de la langue, dans cette langue elle-même, utilisé quand on demande au LLM
# d'écrire du texte dans la langue de la session (profile_description, match_reason...).
LANGUAGE_NAMES: dict[SupportedLanguage, str] = {
    "fr": "français",
    "en": "anglais",
    "es": "espagnol",
    "de": "allemand",
    "ar": "arabe",
    "ru": "russe",
}
