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
    top_notes = formula.get("top_notes", [])
    heart_notes = formula.get("heart_notes", [])
    base_notes = formula.get("base_notes", [])
    notes = top_notes + heart_notes + base_notes
    notes_text = ", ".join(notes)
    profile = formula.get("profile", "")
    description = formula.get("profile_description", "")
    formula_type = formula.get("formula_type", "mix")

    if language == "en":
        return f"""High-end luxury perfume advertisement, portrait orientation, A5 format.

A single elegant perfume bottle centered in the composition, surrounded by its key ingredients rendered as realistic botanical elements: {notes_text}.

Flat lay composition with dramatic natural shadows on a solid background whose color reflects the scent mood.

Scattered petals, sliced fruits or leaves arranged artfully around the bottle.

Vivid, saturated colors. Editorial commercial product photography style. No text, no people, no hands, no existing perfume brand names, no recognizable luxury branding or logos. Ultra sharp, high resolution.

The image must reflect this fragrance identity:
- Profile: {profile}
- Formula type: {formula_type}
- Profile description: {description}
- Top notes: {", ".join(top_notes)}
- Heart notes: {", ".join(heart_notes)}
- Base notes: {", ".join(base_notes)}"""

    return f"""Publicité de parfum de luxe haut de gamme, orientation portrait, format A5.

Un unique flacon de parfum élégant centré dans la composition, entouré de ses ingrédients clés représentés comme des éléments botaniques réalistes : {notes_text}.

Composition en flat lay avec des ombres naturelles marquées sur un fond uni dont la couleur reflète l’humeur olfactive du parfum.

Pétales, fruits tranchés ou feuilles disposés avec soin autour du flacon.

Couleurs vives et saturées. Style de photographie publicitaire éditoriale et commerciale. Sans texte, sans personne, sans mains, sans nom de marque de parfum existante, sans logo ni branding de luxe reconnaissable. Ultra net, haute résolution.

L’image doit refléter cette identité parfum :
- Profil : {profile}
- Type de formule : {formula_type}
- Description du profil : {description}
- Notes de tête : {", ".join(top_notes)}
- Notes de cœur : {", ".join(heart_notes)}
- Notes de fond : {", ".join(base_notes)}"""


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
