import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database import crud
from app.services import cloudinary_service, question_translation_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ── Schémas Questions ──────────────────────────────────────────────────

class ChoiceCreate(BaseModel):
    text: str
    image_url: str | None = None
    language: str


class ChoiceUpdate(BaseModel):
    text: str | None = None
    image_url: str | None = None
    language: str | None = None


class ChoiceResponse(BaseModel):
    id: int
    question_id: int
    text: str
    image_url: str | None
    language: str

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    text: str
    language: str
    is_active: bool = True
    group_ids: list[int] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    text: str | None = None
    language: str | None = None
    is_active: bool | None = None
    group_ids: list[int] | None = None


class QuestionGroupMiniResponse(BaseModel):
    id: int
    name: str
    is_active: bool

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    text: str
    language: str
    is_active: bool
    choices: list[ChoiceResponse] = Field(default_factory=list)
    groups: list[QuestionGroupMiniResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class QuestionGroupCreate(BaseModel):
    name: str
    is_active: bool = True


class QuestionGroupUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class QuestionMiniResponse(BaseModel):
    id: int
    text: str
    language: str
    is_active: bool

    class Config:
        from_attributes = True


class QuestionGroupResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    questions: list[QuestionMiniResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ── Schémas Ingrédients ───────────────────────────────────────────────

class IngredientCreate(BaseModel):
    name: str
    type: str           # top, heart, base
    category: str | None = None
    language: str
    description: str | None = None
    intensity: str | None = None
    allergens: list[str] | None = None
    is_active: bool = True


class IngredientUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    category: str | None = None
    language: str | None = None
    description: str | None = None
    intensity: str | None = None
    allergens: list[str] | None = None
    is_active: bool | None = None


class IngredientResponse(BaseModel):
    id: int
    name: str
    type: str
    category: str | None
    language: str
    description: str | None
    intensity: str | None
    allergens: list[str] | None
    is_active: bool

    class Config:
        from_attributes = True


# ── Routes Questions ───────────────────────────────────────────────────

@router.get("/questions", response_model=list[QuestionResponse])
async def list_questions(
    language: str | None = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_questions(db, language=language, active_only=active_only)


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    question = await crud.get_question_by_id(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return question


@router.get("/questions/{question_id}/translations", response_model=list[QuestionResponse])
async def get_question_translations(question_id: int, db: AsyncSession = Depends(get_db)):
    """Les variantes de langue (questions sœurs) générées par traduction automatique à
    partir de cette question — utilisé par l'admin pour vérifier le résultat sans changer
    de filtre de langue. Liste vide si la question n'a pas (encore) de traductions."""
    question = await crud.get_question_by_id(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")
    if not question.translation_group_id:
        return []
    siblings = await crud.get_questions_by_translation_group(db, question.translation_group_id)
    return [s for s in siblings if s.id != question_id]


@router.post("/questions", response_model=QuestionResponse, status_code=201)
async def create_question(body: QuestionCreate, db: AsyncSession = Depends(get_db)):
    """Crée la question dans la langue demandée. Si la langue est le français (saisie admin
    normale), traduit automatiquement le texte et crée en plus une question sœur par autre
    langue supportée, reliées entre elles via translation_group_id — l'admin ne saisit donc
    le questionnaire qu'une fois, en français."""
    data = body.model_dump()
    try:
        if data["language"] != "fr":
            return await crud.create_question(db, **data)

        translation_group_id = str(uuid.uuid4())
        fr_question = await crud.create_question(db, **data, translation_group_id=translation_group_id)

        translations = await question_translation_service.translate_text(data["text"])
        for lang, translated_text in translations.items():
            await crud.create_question(
                db,
                text=translated_text,
                language=lang,
                is_active=data["is_active"],
                group_ids=data["group_ids"],
                translation_group_id=translation_group_id,
            )

        return await crud.get_question_by_id(db, fr_question.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: int, body: QuestionUpdate, db: AsyncSession = Depends(get_db)):
    try:
        updated = await crud.update_question(db, question_id, **body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return updated


@router.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: int, db: AsyncSession = Depends(get_db)):
    if not await crud.delete_question(db, question_id):
        raise HTTPException(status_code=404, detail="Question introuvable")


@router.get("/question-groups", response_model=list[QuestionGroupResponse])
async def list_question_groups(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_question_groups(db, active_only=active_only)


@router.get("/question-groups/{group_id}", response_model=QuestionGroupResponse)
async def get_question_group(group_id: int, db: AsyncSession = Depends(get_db)):
    group = await crud.get_question_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Groupe de questions introuvable")
    return group


@router.post("/question-groups", response_model=QuestionGroupResponse, status_code=201)
async def create_question_group(body: QuestionGroupCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_question_group(db, **body.model_dump())


@router.patch("/question-groups/{group_id}", response_model=QuestionGroupResponse)
async def update_question_group(group_id: int, body: QuestionGroupUpdate, db: AsyncSession = Depends(get_db)):
    updated = await crud.update_question_group(db, group_id, **body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Groupe de questions introuvable")
    return updated


@router.delete("/question-groups/{group_id}", status_code=204)
async def delete_question_group(group_id: int, db: AsyncSession = Depends(get_db)):
    if not await crud.delete_question_group(db, group_id):
        raise HTTPException(status_code=404, detail="Groupe de questions introuvable")


# ── Routes Choix ──────────────────────────────────────────────────────

@router.post("/questions/{question_id}/choices", response_model=ChoiceResponse, status_code=201)
async def create_choice(question_id: int, body: ChoiceCreate, db: AsyncSession = Depends(get_db)):
    """Crée le choix dans la langue de sa question. Si la question est française et a des
    questions sœurs traduites (translation_group_id), traduit le texte du choix et crée le
    choix correspondant sur chacune des questions sœurs, avec la même image."""
    question = await crud.get_question_by_id(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    data = body.model_dump()
    has_siblings = question.language == "fr" and bool(question.translation_group_id)
    choice_translation_group_id = str(uuid.uuid4()) if has_siblings else None
    choice = await crud.create_choice(
        db, question_id=question_id, translation_group_id=choice_translation_group_id, **data
    )

    if has_siblings:
        siblings = await crud.get_questions_by_translation_group(db, question.translation_group_id)
        other_siblings = [s for s in siblings if s.id != question_id]
        if other_siblings:
            translations = await question_translation_service.translate_text(data["text"])
            for sibling in other_siblings:
                translated_text = translations.get(sibling.language, data["text"])
                await crud.create_choice(
                    db,
                    question_id=sibling.id,
                    text=translated_text,
                    image_url=data.get("image_url"),
                    language=sibling.language,
                    translation_group_id=choice_translation_group_id,
                )

    return choice


@router.patch("/choices/{choice_id}", response_model=ChoiceResponse)
async def update_choice(choice_id: int, body: ChoiceUpdate, db: AsyncSession = Depends(get_db)):
    updated = await crud.update_choice(db, choice_id, **body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Choix introuvable")
    return updated


@router.delete("/choices/{choice_id}", status_code=204)
async def delete_choice(choice_id: int, db: AsyncSession = Depends(get_db)):
    choice = await crud.get_choice_by_id(db, choice_id)
    if not choice:
        raise HTTPException(status_code=404, detail="Choix introuvable")
    if choice.image_url and "cloudinary" in choice.image_url:
        cloudinary_service.delete_choice_image(choice.image_url)
    if not await crud.delete_choice(db, choice_id):
        raise HTTPException(status_code=404, detail="Choix introuvable")


@router.post("/choices/{choice_id}/image", response_model=ChoiceResponse)
async def upload_choice_image(
    choice_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    choice = await crud.get_choice_by_id(db, choice_id)
    if not choice:
        raise HTTPException(status_code=404, detail="Choix introuvable")

    allowed = {"image/", "application/octet-stream"}
    if file.content_type and not any(file.content_type.startswith(p) for p in allowed):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Le fichier est vide")

    try:
        image_url = cloudinary_service.upload_choice_image(choice_id, file_bytes, file.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    updated = await crud.update_choice(db, choice_id, image_url=image_url)

    # Répercute la même image sur les choix traduits (les autres langues réutilisent
    # exactement la même illustration que le choix français).
    if choice.translation_group_id:
        siblings = await crud.get_choices_by_translation_group(db, choice.translation_group_id)
        for sibling in siblings:
            if sibling.id != choice_id:
                await crud.update_choice(db, sibling.id, image_url=image_url)

    return updated


# ── Routes Ingrédients ────────────────────────────────────────────────

@router.get("/ingredients", response_model=list[IngredientResponse])
async def list_ingredients(
    language: str | None = Query(None),
    type: str | None = Query(None),
    category: str | None = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_ingredients(db, language=language, type=type, category=category, active_only=active_only)


@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(ingredient_id: int, db: AsyncSession = Depends(get_db)):
    ingredient = await crud.get_ingredient_by_id(db, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingrédient introuvable")
    return ingredient


@router.post("/ingredients", response_model=IngredientResponse, status_code=201)
async def create_ingredient(body: IngredientCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_ingredient(db, **body.model_dump())


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient(ingredient_id: int, body: IngredientUpdate, db: AsyncSession = Depends(get_db)):
    updated = await crud.update_ingredient(db, ingredient_id, **body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Ingrédient introuvable")
    return updated


@router.delete("/ingredients/{ingredient_id}", status_code=204)
async def delete_ingredient(ingredient_id: int, db: AsyncSession = Depends(get_db)):
    if not await crud.delete_ingredient(db, ingredient_id):
        raise HTTPException(status_code=404, detail="Ingrédient introuvable")
