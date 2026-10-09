import boto3

from app.config import get_settings

# Préfixés sous ateliers/ pour profiter de la bucket policy S3 existante
# (seul ateliers/ est rendu public en lecture — voir sdp-dashboard/server/services/s3.ts).
CHOICES_PREFIX = "ateliers/lylo-choices/"
MOODBOARDS_PREFIX = "ateliers/lylo-moodboards/"
BRANDING_PREFIX = "ateliers/lylo-branding/"


def _client():
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.aws_s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def _public_url(key: str) -> str:
    settings = get_settings()
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_s3_region}.amazonaws.com/{key}"


def _upload(key: str, file_bytes: bytes, content_type: str | None) -> str:
    settings = get_settings()
    if not settings.aws_access_key_id or not settings.aws_secret_access_key or not settings.aws_s3_bucket:
        raise RuntimeError("Configuration AWS S3 manquante")

    try:
        _client().put_object(
            Bucket=settings.aws_s3_bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise RuntimeError(f"Échec de l'upload S3: {exc}") from exc
    return _public_url(key)


def _delete(key: str) -> None:
    settings = get_settings()
    try:
        _client().delete_object(Bucket=settings.aws_s3_bucket, Key=key)
    except Exception:
        pass


def _extract_ext(filename: str | None, default: str) -> str:
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return default


def upload_choice_image(choice_id: int, file_bytes: bytes, filename: str | None = None) -> str:
    """Upload une image de choix sur S3 et retourne l'URL publique."""
    ext = _extract_ext(filename, "jpg")
    key = f"{CHOICES_PREFIX}{choice_id}.{ext}"
    return _upload(key, file_bytes, _content_type_for_ext(ext))


def delete_choice_image(image_url: str) -> None:
    """Supprime une image de choix S3 à partir de son URL publique."""
    prefix = _public_url(CHOICES_PREFIX)
    if not image_url.startswith(prefix):
        return
    key = f"{CHOICES_PREFIX}{image_url[len(prefix):]}"
    _delete(key)


def upload_moodboard_image(notes_key: str, file_bytes: bytes, filename: str | None = None) -> tuple[str, str]:
    """Upload un moodboard sur S3 et retourne (url, key)."""
    ext = _extract_ext(filename, "png")
    key = f"{MOODBOARDS_PREFIX}{notes_key}.{ext}"
    url = _upload(key, file_bytes, _content_type_for_ext(ext))
    return url, key


def upload_project_logo(file_bytes: bytes, filename: str | None, content_type: str | None) -> str:
    """Upload le logo secondaire du projet sur S3 et retourne l'URL publique."""
    ext = _extract_ext(filename, "png")
    key = f"{BRANDING_PREFIX}logo_{_timestamp()}.{ext}"
    return _upload(key, file_bytes, content_type or _content_type_for_ext(ext))


def delete_project_logo(image_url: str) -> None:
    """Supprime le logo secondaire du projet sur S3 à partir de son URL publique."""
    prefix = _public_url(BRANDING_PREFIX)
    if not image_url.startswith(prefix):
        return
    key = f"{BRANDING_PREFIX}{image_url[len(prefix):]}"
    _delete(key)


def _timestamp() -> int:
    import time

    return int(time.time() * 1000)


def _content_type_for_ext(ext: str) -> str:
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "gif": "image/gif",
    }.get(ext.lower(), "application/octet-stream")
