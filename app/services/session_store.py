from datetime import datetime, timezone
from threading import Lock

_lock = Lock()

_meta: dict[str, dict] = {}
_answers: dict[str, dict] = {}
_profiles: dict[str, dict] = {}
_generated_formulas: dict[str, list] = {}
_selected_formula: dict[str, dict] = {}
_index: set[str] = set()


REQUIRED_PROFILE_FIELDS = {"first_name", "gender", "age", "has_allergies"}


def save_session_meta(
    session_id: str,
    language: str,
    voice_gender: str,
    voice_id: str,
    room_name: str,
    questions: list,
    mode: str = "guided",
    customer_email: str | None = None,
) -> None:
    mapping = {
        "language": language,
        "voice_gender": voice_gender,
        "voice_id": voice_id,
        "room_name": room_name,
        "questions": questions,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if customer_email:
        mapping["customer_email"] = customer_email
    with _lock:
        _meta[session_id] = mapping
        _index.add(session_id)


def get_session_meta(session_id: str) -> dict | None:
    with _lock:
        return dict(_meta[session_id]) if session_id in _meta else None


def list_session_ids() -> list[str]:
    with _lock:
        return list(_index)


def save_answer(
    session_id: str,
    question_id: int,
    question_text: str,
    top_2: list[str],
    bottom_2: list[str],
) -> None:
    with _lock:
        if session_id not in _answers:
            _answers[session_id] = {}
        _answers[session_id][str(question_id)] = {
            "question": question_text,
            "top_2": top_2,
            "bottom_2": bottom_2,
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }


def get_session_answers(session_id: str) -> dict | None:
    with _lock:
        if session_id not in _meta:
            return None
        return {
            "session_id": session_id,
            **_meta[session_id],
            "answers": dict(_answers.get(session_id, {})),
        }


def save_user_profile(session_id: str, field: str, value: str) -> None:
    with _lock:
        if session_id not in _profiles:
            _profiles[session_id] = {}
        _profiles[session_id][field] = value


def get_user_profile(session_id: str) -> dict | None:
    with _lock:
        profile = _profiles.get(session_id)
        return dict(profile) if profile else None


def is_profile_complete(session_id: str) -> bool:
    with _lock:
        profile = _profiles.get(session_id, {})
        if not REQUIRED_PROFILE_FIELDS.issubset(profile.keys()):
            return False
        if profile.get("has_allergies", "").lower() in ("oui", "yes") and "allergies" not in profile:
            return False
        return True


def get_missing_profile_fields(session_id: str) -> list[str]:
    with _lock:
        profile = _profiles.get(session_id, {})
        missing = list(REQUIRED_PROFILE_FIELDS - profile.keys())
        if profile.get("has_allergies", "").lower() in ("oui", "yes") and "allergies" not in profile:
            missing.append("allergies")
        return missing


def get_session_state(session_id: str) -> str:
    if is_profile_complete(session_id):
        return "questionnaire"
    return "collecting_profile"


def save_selected_formula(session_id: str, formula_data: dict) -> None:
    with _lock:
        _selected_formula[session_id] = formula_data


def get_selected_formula(session_id: str) -> dict | None:
    with _lock:
        data = _selected_formula.get(session_id)
        return dict(data) if data else None


def save_generated_formulas(session_id: str, formulas: list[dict]) -> None:
    with _lock:
        _generated_formulas[session_id] = formulas


def get_generated_formulas(session_id: str) -> list[dict] | None:
    with _lock:
        data = _generated_formulas.get(session_id)
        return list(data) if data is not None else None


def get_all_sessions() -> list[dict]:
    with _lock:
        ids = list(_index)
    return [d for sid in ids if (d := get_session_answers(sid))]


def delete_session(session_id: str) -> bool:
    with _lock:
        existed = session_id in _meta
        _meta.pop(session_id, None)
        _answers.pop(session_id, None)
        _profiles.pop(session_id, None)
        _generated_formulas.pop(session_id, None)
        _selected_formula.pop(session_id, None)
        _index.discard(session_id)
        return existed
