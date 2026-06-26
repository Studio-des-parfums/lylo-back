import random
import unicodedata
import logging
import asyncio
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database import crud
from app.models.schemas import (
    BatchGenerateRequest,
    ChangeFormulaTypeRequest,
    GenerateFormulasRequest,
    MultiGenerateRequest,
    SaveMultiFormulaRequest,
    ReplaceNoteRequest,
    SaveAnswerRequest,
    SaveFormulaRequest,
    SaveProfileRequest,
    SelectFormulaRequest,
    SendFormulaByReferenceRequest,
    SendFormulaMailRequest,
    StartSessionRequest,
    StartSessionResponse,
)
from app.config import get_settings
from app.services import formula_service, livekit_service, mail_service, pdf_service, session_store, session_service

router = APIRouter(prefix="/api", tags=["sessions"])
logger = logging.getLogger("lylo.sessions_api")
SESSION_DELETE_GRACE_SECONDS = 45


async def _delete_session_after_grace(session_id: str, requested_at: str) -> None:
    await asyncio.sleep(SESSION_DELETE_GRACE_SECONDS)
    meta = session_store.get_session_meta(session_id)
    if meta is None:
        return
    if meta.get("pending_delete_at") != requested_at:
        logger.info("[delete_session] skip cleanup session_id=%s pending_delete_at changed", session_id)
        return
    room_name = meta.get("room_name", f"room_{session_id}")
    session_store.delete_session(session_id)
    await livekit_service.delete_room(room_name)
    logger.info("[delete_session] cleanup applied session_id=%s room=%s", session_id, room_name)


@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(body: StartSessionRequest, db: AsyncSession = Depends(get_db)):
    owner_email = (body.owner_email or body.email or "").strip() or None
    owner_type = None
    owner_id = None
    customer = None
    logger.info(
        "[start_session] request language=%s voice_gender=%s question_count=%s mode=%s input_mode=%s avatar=%s owner_email=%s",
        body.language,
        body.voice_gender,
        body.question_count,
        body.mode,
        body.input_mode,
        body.avatar,
        bool(owner_email),
    )
    if owner_email:
        customer = await crud.get_customer_by_email(db, owner_email)
        if customer:
            owner_type = "customer"
            owner_id = customer.id
            if int(customer.sessions_available) <= 0:
                raise HTTPException(status_code=403, detail="Aucune session disponible")
            max_date = customer.max_date.date() if hasattr(customer.max_date, 'date') else customer.max_date
            if max_date and date.today() > max_date:
                raise HTTPException(status_code=403, detail="Date d'accès expirée")
            await crud.update_customer(db, customer.id, sessions_available=int(customer.sessions_available) - 1)
        else:
            member = await crud.get_team_member_by_email(db, owner_email)
            if not member:
                raise HTTPException(status_code=404, detail="Email introuvable")
            owner_type = "team"
            owner_id = member.id

    try:
        result = await session_service.create_session(
            language=body.language,
            voice_gender=body.voice_gender,
            question_count=body.question_count,
            mode=body.mode,
            input_mode=body.input_mode,
            owner_email=owner_email,
            owner_type=owner_type,
            owner_id=owner_id,
            avatar=body.avatar,
        )
        logger.info(
            "[start_session] success session_id=%s room=%s",
            result["session_id"],
            result["room_name"],
        )
    except Exception as e:
        if owner_email and customer:
            await crud.update_customer(db, customer.id, sessions_available=int(customer.sessions_available) + 1)
        logger.exception("[start_session] failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Erreur création session: {e}")
    return result


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("pending_delete_at"):
        session_store.clear_session_pending_deletion(session_id)
        session.pop("pending_delete_at", None)
        logger.info("[get_session] revived pending deletion session_id=%s", session_id)
    return session


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    meta = session_store.get_session_meta(session_id)
    if meta is None:
        return {"status": "ok", "session_id": session_id, "already_deleted": True}
    requested_at = datetime.now(timezone.utc).isoformat()
    session_store.mark_session_pending_deletion(session_id, requested_at)
    asyncio.create_task(_delete_session_after_grace(session_id, requested_at))
    logger.info(
        "[delete_session] scheduled cleanup session_id=%s grace_seconds=%s",
        session_id,
        SESSION_DELETE_GRACE_SECONDS,
    )
    return {
        "status": "ok",
        "session_id": session_id,
        "scheduled": True,
        "grace_seconds": SESSION_DELETE_GRACE_SECONDS,
    }


@router.get("/session_list")
async def session_list():
    return session_service.list_session_ids()


def _normalize(s: str) -> str:
    """Lowercase + supprime les accents pour comparaison souple."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def _canonical_choice(submitted: str, valid_labels: list[str]) -> str:
    """Retourne le label canonique le plus proche parmi valid_labels.

    Ordre de priorité :
    1. Correspondance exacte (insensible à la casse/accents)
    2. Correspondance du préfixe avant " - " (insensible à la casse/accents)
    3. Le label canonique dont le préfixe normalisé contient le texte soumis
    4. Valeur soumise inchangée si aucun match
    """
    norm_submitted = _normalize(submitted)
    # Préfixe soumis (avant " - ")
    submitted_prefix = norm_submitted.split(" - ")[0].strip()

    for label in valid_labels:
        if _normalize(label) == norm_submitted:
            return label

    for label in valid_labels:
        label_prefix = _normalize(label).split(" - ")[0].strip()
        if label_prefix == submitted_prefix:
            return label

    for label in valid_labels:
        label_prefix = _normalize(label).split(" - ")[0].strip()
        if submitted_prefix in label_prefix or label_prefix in submitted_prefix:
            return label

    return submitted


def _normalize_choices(choices: list[str], valid_labels: list[str]) -> list[str]:
    return [_canonical_choice(c, valid_labels) for c in choices]


@router.post("/session/{session_id}/save-answer")
async def save_answer(session_id: str, body: SaveAnswerRequest):
    if not session_store.is_profile_complete(session_id):
        raise HTTPException(
            status_code=400,
            detail="Profile incomplete, cannot save answers yet",
        )

    # Récupérer les choix valides pour cette question depuis la session
    meta = session_store.get_session_meta(session_id)
    top_2 = body.top_2
    bottom_2 = body.bottom_2
    if meta:
        questions = meta.get("questions", [])
        question = next((q for q in questions if q["id"] == body.question_id), None)
        if question:
            valid_labels = [
                c["label"] if isinstance(c, dict) else c
                for c in question.get("choices", [])
            ]
            top_2 = _normalize_choices(top_2, valid_labels)
            bottom_2 = _normalize_choices(bottom_2, valid_labels)

    session_store.save_answer(
        session_id=session_id,
        question_id=body.question_id,
        question_text=body.question_text,
        top_2=top_2,
        bottom_2=bottom_2,
    )
    return {"status": "ok"}


@router.get("/session/{session_id}/answers")
async def get_answers(session_id: str):
    data = session_store.get_session_answers(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@router.post("/session/{session_id}/save-profile")
async def save_profile(session_id: str, body: SaveProfileRequest):
    session_store.save_user_profile(session_id, body.field, body.value)
    complete = session_store.is_profile_complete(session_id)
    missing = session_store.get_missing_profile_fields(session_id)
    state = "questionnaire" if complete else "collecting_profile"
    return {
        "status": "ok",
        "state": state,
        "profile_complete": complete,
        "missing_fields": missing,
    }


@router.get("/session/{session_id}/state")
async def get_state(session_id: str):
    state = session_store.get_session_state(session_id)
    complete = session_store.is_profile_complete(session_id)
    missing = session_store.get_missing_profile_fields(session_id)
    mail_available = session_store.get_selected_formula(session_id) is not None
    return {
        "state": state,
        "profile_complete": complete,
        "missing_fields": missing,
        "mail_available": mail_available,
    }


@router.get("/session/{session_id}/profile")
async def get_profile(session_id: str):
    profile = session_store.get_user_profile(session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/session/{session_id}/generate-formulas")
async def generate_formulas(session_id: str, body: GenerateFormulasRequest = GenerateFormulasRequest()):
    if not session_store.is_profile_complete(session_id):
        raise HTTPException(
            status_code=400,
            detail="Profile incomplete, cannot generate formulas",
        )
    result = await formula_service.generate_formulas(session_id, force_type=body.formula_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


def _send_formula_mail_bg(session_id: str, formula: dict) -> None:
    # Mail participant
    meta = session_store.get_session_meta(session_id)
    profile = session_store.get_user_profile(session_id) or {}
    participant_email = (
        formula.get("customer_email")
        or profile.get("email")
        or (meta.get("participant_email") if meta else None)
    )
    if participant_email:
        try:
            mail_service.send_mail(participant_email, session_id, formula)
        except Exception as e:
            print(f"[mail] Erreur envoi mail formule au participant {participant_email} : {e}")

    # Mail interne
    internal_email = get_settings().internal_email
    if not internal_email:
        return
    for email in [e.strip() for e in internal_email.split(",") if e.strip()]:
        try:
            mail_service.send_mail(email, session_id, formula)
        except Exception as e:
            print(f"[mail] Erreur envoi mail formule à {email} : {e}")
        try:
            mail_service.send_internal_formula_mail(email, session_id, formula)
        except Exception as e:
            print(f"[mail] Erreur envoi mail fiche complète à {email} : {e}")


def _extract_moodboard_fields(formula: dict) -> dict:
    moodboard = formula.get("moodboard") or {}
    return {
        "moodboard_notes_key": moodboard.get("notes_key"),
        "moodboard_image_url": moodboard.get("image_url"),
    }


@router.post("/session/{session_id}/select-formula")
async def select_formula(
    session_id: str, body: SelectFormulaRequest, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = formula_service.select_formula(session_id, body.formula_index)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    formula = result["formula"]
    meta = session_store.get_session_meta(session_id) or {}
    profile = session_store.get_user_profile(session_id) or {}
    db_formula = await crud.create_generated_formula(
        db,
        session_id=session_id,
        profile=formula.get("profile"),
        formula_type=formula.get("formula_type"),
        top_notes=formula.get("top_notes"),
        heart_notes=formula.get("heart_notes"),
        base_notes=formula.get("base_notes"),
        sizes=formula.get("sizes"),
        customer_name=" ".join(
            part for part in [profile.get("first_name"), profile.get("last_name")] if part
        ) or None,
        customer_email=profile.get("email"),
        language=meta.get("language"),
        **_extract_moodboard_fields(formula),
        participant_id=meta.get("participant_id"),
        owner_type=meta.get("owner_type"),
        owner_team_id=meta.get("owner_id") if meta.get("owner_type") == "team" else None,
        owner_customer_id=meta.get("owner_id") if meta.get("owner_type") == "customer" else None,
    )
    result["reference"] = db_formula.reference

    background_tasks.add_task(_send_formula_mail_bg, session_id, formula)
    return result


@router.post("/session/{session_id}/change-formula-type")
async def change_formula_type(session_id: str, body: ChangeFormulaTypeRequest):
    result = await formula_service.change_selected_formula_type(session_id, body.formula_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/session/{session_id}/available-ingredients/{note_type}")
async def available_ingredients(session_id: str, note_type: str):
    result = await formula_service.get_available_ingredients(session_id, note_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/session/{session_id}/replace-note")
async def replace_note(
    session_id: str, body: ReplaceNoteRequest, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await formula_service.replace_note(
        session_id, body.note_type, body.old_note, body.new_note
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    formula = session_store.get_selected_formula(session_id)
    if formula:
        await crud.update_generated_formula_by_session(
            db,
            session_id=session_id,
            top_notes=formula.get("top_notes"),
            heart_notes=formula.get("heart_notes"),
            base_notes=formula.get("base_notes"),
            sizes=formula.get("sizes"),
            **_extract_moodboard_fields(formula),
        )
        background_tasks.add_task(_send_formula_mail_bg, session_id, formula)
    return result


@router.get("/session/{session_id}/formula/pdf")
async def get_formula_pdf(session_id: str):
    formula = session_store.get_selected_formula(session_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="No formula selected for this session")
    pdf_bytes = pdf_service.generate_formula_pdf(formula)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="formule-{session_id}.pdf"'},
    )


@router.get("/sessions/all-answers")
async def get_all_answers():
    return session_store.get_all_sessions()


@router.get("/questions")
async def get_questions(count: int = 12, language: str = "fr", db: AsyncSession = Depends(get_db)):
    groups = await crud.get_active_question_groups_with_questions(db, language=language)
    if not groups:
        raise HTTPException(status_code=404, detail="Aucun groupe de questions actif disponible")
    selected_group = random.choice(groups)
    questions = session_service.order_questions_for_front(selected_group.name, selected_group.questions)
    selected = questions[:count]
    return {
        "group_id": selected_group.id,
        "group_name": selected_group.name,
        "questions": [
            {
                "id": q.id,
                "question": q.text,
                "choices": [{"label": c.text, "image": c.image_url or ""} for c in q.choices],
            }
            for q in selected
        ]
    }


@router.post("/formulas/send-mail")
async def send_formula_mail(body: SendFormulaMailRequest, background_tasks: BackgroundTasks):
    try:
        mail_service.send_formula_mail_stateless(body.email, body.formula, body.language)
    except Exception as e:
        print(f"[mail] Erreur envoi: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}


@router.post("/formulas/{reference}/send-mail")
async def send_formula_mail_by_reference(
    reference: str,
    body: SendFormulaByReferenceRequest,
    db: AsyncSession = Depends(get_db),
):
    db_formula = await crud.get_generated_formula_by_reference(db, reference)
    if not db_formula:
        raise HTTPException(status_code=404, detail="Formula not found")

    target_email = (body.email or db_formula.customer_email or "").strip()
    if not target_email:
        raise HTTPException(
            status_code=400,
            detail="Missing email: provide one or store a customer_email on the formula",
        )

    if body.email and body.email.strip() != (db_formula.customer_email or "").strip():
        db_formula = await crud.update_generated_formula_by_reference(
            db,
            reference,
            customer_email=target_email,
        )
        if not db_formula:
            raise HTTPException(status_code=404, detail="Formula not found")

    formula = {
        "reference": db_formula.reference,
        "session_id": db_formula.session_id,
        "profile": db_formula.profile,
        "formula_type": db_formula.formula_type,
        "top_notes": db_formula.top_notes,
        "heart_notes": db_formula.heart_notes,
        "base_notes": db_formula.base_notes,
        "sizes": db_formula.sizes,
        "customer_name": db_formula.customer_name,
        "customer_email": db_formula.customer_email,
        "language": db_formula.language,
        "participant_id": db_formula.participant_id,
        "owner_type": db_formula.owner_type,
        "owner_team_id": db_formula.owner_team_id,
        "owner_customer_id": db_formula.owner_customer_id,
        "created_at": db_formula.created_at.isoformat() if db_formula.created_at else None,
    }

    try:
        mail_service.send_formula_mail_stateless(
            target_email,
            formula,
            db_formula.language or "fr",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")

    return {
        "status": "ok",
        "reference": db_formula.reference,
        "email": target_email,
    }


@router.get("/formulas")
async def list_formulas(
    search: str = "",
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    skip = (max(page, 1) - 1) * limit
    rows, total = await crud.get_formulas(db, search=search.strip(), skip=skip, limit=limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": [
            {
                "id": r.id,
                "reference": r.reference,
                "session_id": r.session_id,
                "profile": r.profile,
                "formula_type": r.formula_type,
                "top_notes": r.top_notes,
                "heart_notes": r.heart_notes,
                "base_notes": r.base_notes,
                "sizes": r.sizes,
                "customer_name": r.customer_name,
                "customer_email": r.customer_email,
                "language": r.language,
                "moodboard_notes_key": r.moodboard_notes_key,
                "moodboard_image_url": r.moodboard_image_url,
                "participant_id": r.participant_id,
                "owner_type": r.owner_type,
                "owner_team_id": r.owner_team_id,
                "owner_customer_id": r.owner_customer_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.post("/formulas/save")
async def save_formula(body: SaveFormulaRequest, db: AsyncSession = Depends(get_db)):
    formula = body.formula
    db_formula = await crud.create_generated_formula(
        db,
        session_id=formula.get("session_id") or "quiz",
        profile=formula.get("profile"),
        formula_type=formula.get("formula_type"),
        top_notes=formula.get("top_notes"),
        heart_notes=formula.get("heart_notes"),
        base_notes=formula.get("base_notes"),
        sizes=formula.get("sizes"),
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        language=body.language,
        **_extract_moodboard_fields(formula),
        participant_id=body.participant_id,
    )
    return {"reference": db_formula.reference}


@router.post("/formulas/generate")
async def batch_generate_formulas(body: BatchGenerateRequest):
    answers = {
        str(a.question_id): {
            "question": a.question_text,
            "top_2": a.top_2,
            "bottom_2": a.bottom_2,
        }
        for a in body.answers
    }
    result = await formula_service.generate_formulas_stateless(
        answers=answers,
        language=body.language,
        has_allergies=body.has_allergies,
        user_allergens_raw=body.allergies or "",
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/formulas/generate-multi")
async def multi_generate_formulas(body: MultiGenerateRequest):
    """Génère 2 formules pour chaque participant (mode visuel multi-utilisateurs)."""
    results = []
    for participant in body.participants:
        answers = {
            str(a.question_id): {
                "question": a.question_text,
                "top_2": a.top_2,
                "bottom_2": a.bottom_2,
            }
            for a in participant.answers
        }
        result = await formula_service.generate_formulas_stateless(
            answers=answers,
            language=body.language,
            has_allergies=participant.has_allergies,
            user_allergens_raw=participant.allergies or "",
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"[{participant.color}] {result['error']}")
        results.append({
            "color": participant.color,
            "formulas": result.get("formulas", []),
        })
    return {"participants": results}


@router.post("/formulas/save-multi")
async def save_multi_formulas(body: SaveMultiFormulaRequest, db: AsyncSession = Depends(get_db)):
    """Sauvegarde la formule sélectionnée par chaque participant, avec référence individuelle."""
    saved = []
    for sel in body.selections:
        formula = sel.formula
        db_formula = await crud.create_generated_formula(
            db,
            session_id=formula.get("session_id") or "quiz-multi",
            profile=formula.get("profile"),
            formula_type=formula.get("formula_type"),
            top_notes=formula.get("top_notes"),
            heart_notes=formula.get("heart_notes"),
            base_notes=formula.get("base_notes"),
            sizes=formula.get("sizes"),
            customer_name=sel.customer_name,
            customer_email=sel.customer_email,
            language=body.language,
            **_extract_moodboard_fields(formula),
            input_mode=body.input_mode,
            participant_color=sel.color,
            participant_id=sel.participant_id,
        )
        saved.append({
            "color": sel.color,
            "reference": db_formula.reference,
        })
    return {"saved": saved}
