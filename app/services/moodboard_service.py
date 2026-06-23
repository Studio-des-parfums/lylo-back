import base64
import hashlib
import json
import logging
import unicodedata

from openai import AsyncOpenAI
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database.connection import AsyncSessionLocal
from app.database import crud
from app.services import cloudinary_service

logger = logging.getLogger("lylo.moodboard")


def _normalize_note(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _sorted_normalized_notes(values: list[str]) -> list[str]:
    return sorted(_normalize_note(value) for value in values if value and value.strip())


def build_notes_key(formula: dict) -> str:
    payload = {
        "top_notes": _sorted_normalized_notes(formula.get("top_notes", [])),
        "heart_notes": _sorted_normalized_notes(formula.get("heart_notes", [])),
        "base_notes": _sorted_normalized_notes(formula.get("base_notes", [])),
    }
    serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _build_moodboard_prompt(formula: dict, language: str) -> str:
    top_notes = ", ".join(formula.get("top_notes", []))
    heart_notes = ", ".join(formula.get("heart_notes", []))
    base_notes = ", ".join(formula.get("base_notes", []))
    profile = formula.get("profile", "")
    description = formula.get("profile_description", "")
    formula_type = formula.get("formula_type", "mix")

    if language == "en":
        return f"""Create a living, immersive luxury fragrance artwork with no text, no typography, no bottle, and no people.

This must not look like a simple 4-image collage, reference board, grid, or scrapbook. Create one cohesive visual world with depth, atmosphere, motion, and emotional intensity, as if the fragrance has come alive in a cinematic editorial scene.

The artwork must visually express this olfactory formula:
- Profile: {profile}
- Formula type: {formula_type}
- Profile description: {description}
- Top notes: {top_notes}
- Heart notes: {heart_notes}
- Base notes: {base_notes}

Style direction: high-end fashion campaign, cinematic composition, sensual materials, layered textures, organic transitions between ingredients, luminous haze, subtle particles, fluid movement, atmospheric depth, refined highlights, elegant shadows, premium contemporary luxury.

Make the image feel alive and sensory: drifting petals, suspended mist, glowing citrus oils, smoky woods, soft fabric movement, mineral reflections, botanical traces dissolving into one another. The composition should feel curated yet organic, like a dreamlike olfactory landscape.

Avoid literal packshot aesthetics. Avoid a flat collage. Avoid tiled frames. Prefer one unified artistic composition with strong visual storytelling."""

    return f"""Crée une image de parfum de luxe immersive et vivante, sans texte, sans typographie, sans flacon et sans personnage.

L’image ne doit surtout pas ressembler à un simple collage de 4 images, ni à une grille, ni à un scrapbook. Elle doit former un seul univers visuel cohérent, profond, atmosphérique et cinématographique, comme si le parfum prenait vie.

L’image doit exprimer visuellement cette formule olfactive :
- Profil : {profile}
- Type de formule : {formula_type}
- Description du profil : {description}
- Notes de tête : {top_notes}
- Notes de cœur : {heart_notes}
- Notes de fond : {base_notes}

Direction artistique : campagne mode haut de gamme, composition cinématographique, matières sensuelles, textures superposées, transitions organiques entre les ingrédients, brume lumineuse, particules subtiles, sensation de mouvement, profondeur atmosphérique, reflets raffinés, ombres élégantes, luxe contemporain.

L’image doit sembler vivante et sensorielle : pétales en suspension, vapeur délicate, huiles d’agrumes lumineuses, bois fumés, tissus en mouvement, éclats minéraux, traces botaniques qui se fondent les unes dans les autres. La composition doit être éditoriale, organique et presque onirique, comme un paysage olfactif.

Évite absolument l’effet packshot. Évite le collage plat. Évite les cases séparées. Privilégie une seule composition artistique forte avec une vraie narration visuelle."""


async def _generate_moodboard_image_bytes(formula: dict, language: str) -> bytes:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = _build_moodboard_prompt(formula, language)

    response = await client.images.generate(
        model=settings.openai_image_model,
        prompt=prompt,
        size="1024x1024",
    )
    b64_json = response.data[0].b64_json
    if not b64_json:
        raise RuntimeError("Le provider image n'a pas renvoyé de b64_json")
    return base64.b64decode(b64_json)


async def attach_moodboard(formula: dict, language: str) -> dict:
    notes_key = build_notes_key(formula)

    async with AsyncSessionLocal() as db:
        cached = await crud.get_formula_moodboard_by_notes_key(db, notes_key)
        if cached:
            formula["moodboard"] = {
                "notes_key": notes_key,
                "image_url": cached.image_url,
                "cached": True,
            }
            return formula

        image_bytes = await _generate_moodboard_image_bytes(formula, language)
        image_url, public_id = cloudinary_service.upload_moodboard_image(notes_key, image_bytes)
        try:
            created = await crud.create_formula_moodboard(
                db,
                notes_key=notes_key,
                top_notes=formula.get("top_notes", []),
                heart_notes=formula.get("heart_notes", []),
                base_notes=formula.get("base_notes", []),
                image_url=image_url,
                cloudinary_public_id=public_id,
            )
        except IntegrityError:
            await db.rollback()
            created = await crud.get_formula_moodboard_by_notes_key(db, notes_key)
            if not created:
                raise

    formula["moodboard"] = {
        "notes_key": notes_key,
        "image_url": created.image_url,
        "cached": False,
    }
    return formula


async def attach_moodboard_safe(formula: dict, language: str) -> dict:
    try:
        return await attach_moodboard(formula, language)
    except Exception as exc:
        logger.exception("[moodboard] échec génération/cache image: %s", exc)
        formula["moodboard"] = None
        return formula
