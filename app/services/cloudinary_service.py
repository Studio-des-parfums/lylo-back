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


def upload_choice_image(choice_id: int, file_bytes: bytes) -> str:
    """Upload une image de choix sur Cloudinary et retourne l'URL sécurisée."""
    _configure()
    public_id = f"lylo/choices/{choice_id}"
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            fetch_format="auto",
            quality="auto",
        )
    except Exception as exc:
        raise RuntimeError("Échec de l'upload Cloudinary") from exc
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
