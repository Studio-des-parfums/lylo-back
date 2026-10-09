from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.languages import SUPPORTED_LANGUAGES, SupportedLanguage


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LiveKit
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    # Nom du worker agent enregistré/dispatché sur LiveKit Cloud. Le même projet
    # LiveKit Cloud est partagé entre prod (Railway) et le développement local — si
    # les deux tournent avec le même nom, LiveKit peut dispatcher une session créée
    # sur un backend vers l'agent tournant sur l'AUTRE, qui ne connaît pas cette
    # session (session_store est local à chaque process) → la session ne démarre
    # jamais. En local, mets LIVEKIT_AGENT_NAME=lylo-dev dans le .env pour isoler
    # complètement ton environnement de test de la prod.
    livekit_agent_name: str = "lylo"

    # Deepgram
    deepgram_api_key: str

    # Cartesia
    cartesia_api_key: str

    # Voices
    voice_fr_female: str
    voice_fr_male: str
    voice_en_female: str
    voice_en_male: str
    voice_es_female: str = ""
    voice_es_male: str = ""
    voice_de_female: str = ""
    voice_de_male: str = ""
    voice_ar_female: str = ""
    voice_ar_male: str = ""
    voice_ru_female: str = ""
    voice_ru_male: str = ""

    # OpenAI
    openai_api_key: str
    openai_image_model: str = "gpt-image-1"

    # Backend
    backend_url: str = "http://localhost:8000"

    # Ingredients API (dashboard)
    ingredients_api_url: str = "https://sdp-dashboard-back-production.up.railway.app"
    ingredients_box_set: str = "Odyssée"

    # Email
    resend_api_key: str = ""
    resend_from: str = "onboarding@resend.dev"

    # SMTP (legacy fallback)
    smtp_host: str = "ssl0.ovh.net"
    smtp_port: int = 587
    smtp_use_ssl: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    internal_email: str = ""

    # Database (PostgreSQL)
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # PrintNode
    printnode_api_key: str = ""

    # Cloudinary (legacy, conservé pour les images déjà uploadées)
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # AWS S3 (bucket partagé avec sdp-dashboard, voir server/services/s3.ts)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_s3_region: str = "eu-west-3"

    @property
    def voice_mapping(self) -> dict[SupportedLanguage, dict[str, str]]:
        return {
            "fr": {"female": self.voice_fr_female, "male": self.voice_fr_male},
            "en": {"female": self.voice_en_female, "male": self.voice_en_male},
            "es": {"female": self.voice_es_female, "male": self.voice_es_male},
            "de": {"female": self.voice_de_female, "male": self.voice_de_male},
            "ar": {"female": self.voice_ar_female, "male": self.voice_ar_male},
            "ru": {"female": self.voice_ru_female, "male": self.voice_ru_male},
        }

    def get_voice_id(self, language: SupportedLanguage, voice_gender: str) -> str:
        voice_id = self.voice_mapping[language][voice_gender]
        if not voice_id:
            raise ValueError(
                f"Voix manquante pour la langue '{language}' ({voice_gender}) : "
                f"définis VOICE_{language.upper()}_{voice_gender.upper()} dans .env"
            )
        return voice_id


@lru_cache
def get_settings() -> Settings:
    return Settings()
