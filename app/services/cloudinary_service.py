from io import BytesIO

import cloudinary
import cloudinary.uploader

from app.config import get_settings


def _configure():
    settings = get_settings()
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def upload_choice_image(choice_id: int, file_bytes: bytes, filename: str | None = None) -> str:
    """Upload une image de choix sur Cloudinary et retourne l'URL sécurisée."""
    settings = get_settings()
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise RuntimeError("Configuration Cloudinary manquante")

    _configure()
    public_id = f"lylo/choices/{choice_id}"
    file_obj = BytesIO(file_bytes)
    file_obj.name = filename or f"choice_{choice_id}.bin"
    try:
        result = cloudinary.uploader.upload(
            file_obj,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            fetch_format="auto",
            quality="auto",
        )
    except Exception as exc:
        raise RuntimeError(f"Échec de l'upload Cloudinary: {exc}") from exc
    return result["secure_url"]


def delete_choice_image(image_url: str) -> None:
    """Supprime une image Cloudinary à partir de son URL."""
    _configure()
    # Extrait le public_id depuis l'URL : .../lylo/choices/city
    try:
        public_id = "lylo/choices/" + image_url.split("/lylo/choices/")[-1].rsplit(".", 1)[0]
        cloudinary.uploader.destroy(public_id)
    except Exception:
        pass
