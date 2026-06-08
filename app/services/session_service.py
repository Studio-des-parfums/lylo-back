import random
import uuid
import logging

from app.config import get_settings
from app.database.connection import AsyncSessionLocal
from app.database import crud
from app.services.livekit_service import create_token, create_room_with_agent
from app.services import session_store

logger = logging.getLogger("lylo.session")


async def _load_questions_from_db(language: str, count: int) -> list[dict]:
    """Charge les questions depuis la BDD dans un ordre aléatoire."""
    async with AsyncSessionLocal() as db:
        questions = await crud.get_all_questions(db, language=language, active_only=True)

    random.shuffle(questions)
    selected = questions[:count]

    result = []
    for q in selected:
        choices = list(q.choices)
        random.shuffle(choices)
        result.append({
            "id": q.id,
            "question": q.text,
            "choices": [
                {"label": c.text, "image": c.image_url or ""}
                for c in choices
            ],
        })
    return result


async def create_session(language: str, voice_gender: str, question_count: int, mode: str = "guided", input_mode: str = "voice", customer_email: str | None = None, avatar: bool = True) -> dict:
    settings = get_settings()

    session_id = str(uuid.uuid4())
    room_name = f"room_{session_id}"
    user_identity = f"user_{session_id}"

    voice_id = settings.voice_mapping[language][voice_gender]
    questions = await _load_questions_from_db(language, question_count)

    user_token = create_token(user_identity, room_name)

    # Save metadata BEFORE dispatching the agent so it can find the session immediately
    session_store.save_session_meta(
        session_id=session_id,
        language=language,
        voice_gender=voice_gender,
        voice_id=voice_id,
        room_name=room_name,
        questions=questions,
        mode=mode,
        input_mode=input_mode,
        customer_email=customer_email,
        avatar=avatar,
    )
    logger.info(
        "[session] session meta saved session_id=%s room=%s language=%s voice_gender=%s questions=%s mode=%s input_mode=%s avatar=%s",
        session_id,
        room_name,
        language,
        voice_gender,
        len(questions),
        mode,
        input_mode,
        avatar,
    )

    try:
        logger.info("[session] creating LiveKit room and dispatch for session_id=%s room=%s", session_id, room_name)
        await create_room_with_agent(room_name)
        logger.info("[session] LiveKit room ready for session_id=%s room=%s", session_id, room_name)
    except Exception:
        logger.exception("[session] failed to create LiveKit room for session_id=%s room=%s", session_id, room_name)
        session_store.delete_session(session_id)
        raise

    return {
        "session_id": session_id,
        "room_name": room_name,
        "token": user_token,
        "livekit_url": settings.livekit_url,
        "identity": user_identity,
    }


def get_session(session_id: str) -> dict | None:
    return session_store.get_session_meta(session_id)


def list_session_ids() -> list[str]:
    return session_store.list_session_ids()
