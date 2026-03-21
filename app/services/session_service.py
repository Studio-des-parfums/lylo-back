import uuid

from app.config import get_settings
from app.data.questions import QUESTIONS_EN, QUESTIONS_FR, _enrich_questions
from app.services.livekit_service import create_token, create_room_with_agent
from app.services import session_store


async def create_session(language: str, voice_gender: str, question_count: int, mode: str = "guided", customer_email: str | None = None) -> dict:
    settings = get_settings()

    session_id = str(uuid.uuid4())
    room_name = f"room_{session_id}"
    user_identity = f"user_{session_id}"

    voice_id = settings.voice_mapping[language][voice_gender]
    questions_pool = QUESTIONS_FR if language == "fr" else QUESTIONS_EN
    questions = _enrich_questions(questions_pool[:question_count])

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
        customer_email=customer_email,
    )

    await create_room_with_agent(room_name)

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
