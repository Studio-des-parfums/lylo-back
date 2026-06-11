from datetime import date as date_type, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.database.models import (
    Customer,
    GeneratedFormula,
    Ingredient,
    Printer,
    Question,
    QuestionChoice,
    QuestionGroup,
    TeamMember,
)


MAX_QUESTIONS_PER_GROUP = 12


async def get_customer_by_email(db: AsyncSession, email: str) -> Customer | None:
    result = await db.execute(select(Customer).where(Customer.email == email))
    return result.scalar_one_or_none()


async def get_customer_by_id(db: AsyncSession, customer_id: int) -> Customer | None:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


async def get_all_customers(db: AsyncSession) -> list[Customer]:
    result = await db.execute(select(Customer))
    return result.scalars().all()


async def create_customer(db: AsyncSession, **kwargs) -> Customer:
    customer = Customer(**kwargs)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def update_customer(db: AsyncSession, customer_id: int, **kwargs) -> Customer | None:
    customer = await get_customer_by_id(db, customer_id)
    if not customer:
        return None
    for field, value in kwargs.items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer


async def delete_customer(db: AsyncSession, customer_id: int) -> bool:
    customer = await get_customer_by_id(db, customer_id)
    if not customer:
        return False
    await db.delete(customer)
    await db.commit()
    return True


# --- TeamMember CRUD ---

async def get_team_member_by_email(db: AsyncSession, email: str) -> TeamMember | None:
    result = await db.execute(select(TeamMember).where(TeamMember.email == email))
    return result.scalar_one_or_none()


async def get_team_member_by_id(db: AsyncSession, member_id: int) -> TeamMember | None:
    result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    return result.scalar_one_or_none()


async def get_all_team_members(db: AsyncSession) -> list[TeamMember]:
    result = await db.execute(select(TeamMember))
    return result.scalars().all()


async def create_team_member(db: AsyncSession, **kwargs) -> TeamMember:
    member = TeamMember(**kwargs)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_team_member(db: AsyncSession, member_id: int, **kwargs) -> TeamMember | None:
    member = await get_team_member_by_id(db, member_id)
    if not member:
        return None
    for field, value in kwargs.items():
        setattr(member, field, value)
    await db.commit()
    await db.refresh(member)
    return member


async def delete_team_member(db: AsyncSession, member_id: int) -> bool:
    member = await get_team_member_by_id(db, member_id)
    if not member:
        return False
    await db.delete(member)
    await db.commit()
    return True


# --- Printer CRUD ---

async def get_all_printers(db: AsyncSession) -> list[Printer]:
    result = await db.execute(select(Printer))
    return result.scalars().all()


async def get_printer_by_id(db: AsyncSession, printer_id: int) -> Printer | None:
    result = await db.execute(select(Printer).where(Printer.id == printer_id))
    return result.scalar_one_or_none()


async def get_printer_by_location(db: AsyncSession, location: str) -> Printer | None:
    result = await db.execute(
        select(Printer).where(Printer.location == location, Printer.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_printers_by_location(db: AsyncSession, location: str) -> list[Printer]:
    result = await db.execute(
        select(Printer).where(Printer.location == location, Printer.is_active == True)
    )
    return result.scalars().all()


async def create_printer(db: AsyncSession, **kwargs) -> Printer:
    printer = Printer(**kwargs)
    db.add(printer)
    await db.commit()
    await db.refresh(printer)
    return printer


async def update_printer(db: AsyncSession, printer_id: int, **kwargs) -> Printer | None:
    printer = await get_printer_by_id(db, printer_id)
    if not printer:
        return None
    for field, value in kwargs.items():
        setattr(printer, field, value)
    await db.commit()
    await db.refresh(printer)
    return printer


async def delete_printer(db: AsyncSession, printer_id: int) -> bool:
    printer = await get_printer_by_id(db, printer_id)
    if not printer:
        return False
    await db.delete(printer)
    await db.commit()
    return True


# --- GeneratedFormula CRUD ---

async def _generate_reference(db: AsyncSession) -> str:
    today = datetime.now()
    date_str = today.strftime("%d%m%Y")
    prefix = f"lylo-{date_str}-"
    result = await db.execute(
        select(func.count(GeneratedFormula.id)).where(
            GeneratedFormula.reference.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    return f"{prefix}{(count + 1):03d}"


async def create_generated_formula(db: AsyncSession, **kwargs) -> GeneratedFormula:
    reference = await _generate_reference(db)
    formula = GeneratedFormula(reference=reference, **kwargs)
    db.add(formula)
    await db.commit()
    await db.refresh(formula)
    return formula


async def update_generated_formula_by_session(db: AsyncSession, session_id: str, **kwargs) -> GeneratedFormula | None:
    result = await db.execute(
        select(GeneratedFormula).where(GeneratedFormula.session_id == session_id)
    )
    formula = result.scalar_one_or_none()
    if not formula:
        return None
    for field, value in kwargs.items():
        setattr(formula, field, value)
    await db.commit()
    await db.refresh(formula)
    return formula


async def get_generated_formula_by_session(db: AsyncSession, session_id: str) -> GeneratedFormula | None:
    result = await db.execute(
        select(GeneratedFormula).where(GeneratedFormula.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def get_formulas(
    db: AsyncSession, search: str = "", skip: int = 0, limit: int = 50
) -> tuple[list[GeneratedFormula], int]:
    from sqlalchemy import or_
    query = select(GeneratedFormula)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                GeneratedFormula.reference.ilike(pattern),
                GeneratedFormula.customer_email.ilike(pattern),
            )
        )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    rows = await db.execute(
        query.order_by(GeneratedFormula.created_at.desc()).offset(skip).limit(limit)
    )
    return rows.scalars().all(), total


# --- Question CRUD ---

async def get_all_questions(db: AsyncSession, language: str | None = None, active_only: bool = True) -> list[Question]:
    query = select(Question).options(selectinload(Question.choices), selectinload(Question.groups))
    if active_only:
        query = query.where(Question.is_active == True)
    if language:
        query = query.where(Question.language == language)
    result = await db.execute(query)
    return result.scalars().all()


async def get_question_by_id(db: AsyncSession, question_id: int) -> Question | None:
    result = await db.execute(
        select(Question).options(selectinload(Question.choices), selectinload(Question.groups)).where(Question.id == question_id)
    )
    return result.scalar_one_or_none()


async def _get_groups_by_ids(db: AsyncSession, group_ids: list[int]) -> list[QuestionGroup]:
    if not group_ids:
        return []
    result = await db.execute(
        select(QuestionGroup)
        .options(selectinload(QuestionGroup.questions))
        .where(QuestionGroup.id.in_(group_ids))
    )
    groups = result.scalars().all()
    if len(groups) != len(set(group_ids)):
        raise ValueError("Un ou plusieurs groupes de questions sont introuvables")
    return groups


def _validate_question_has_groups(groups: list[QuestionGroup]) -> None:
    if not groups:
        raise ValueError("Une question doit appartenir à au moins un groupe")


def _validate_group_capacity(groups: list[QuestionGroup], *, current_question_id: int | None = None) -> None:
    for group in groups:
        count = sum(1 for question in group.questions if question.id != current_question_id)
        if count >= MAX_QUESTIONS_PER_GROUP:
            raise ValueError(
                f'Le groupe "{group.name}" a déjà atteint la limite de {MAX_QUESTIONS_PER_GROUP} questions'
            )


def _sync_question_groups(question: Question, groups: list[QuestionGroup]) -> None:
    question.groups = groups


async def create_question(db: AsyncSession, **kwargs) -> Question:
    group_ids = kwargs.pop("group_ids", [])
    groups = await _get_groups_by_ids(db, group_ids)
    _validate_question_has_groups(groups)
    _validate_group_capacity(groups)
    question = Question(**kwargs)
    _sync_question_groups(question, groups)
    db.add(question)
    await db.commit()
    return await get_question_by_id(db, question.id)


async def update_question(db: AsyncSession, question_id: int, **kwargs) -> Question | None:
    question = await get_question_by_id(db, question_id)
    if not question:
        return None
    if "group_ids" in kwargs:
        group_ids = kwargs.pop("group_ids") or []
        groups = await _get_groups_by_ids(db, group_ids)
        _validate_question_has_groups(groups)
        _validate_group_capacity(groups, current_question_id=question_id)
        _sync_question_groups(question, groups)
    for field, value in kwargs.items():
        setattr(question, field, value)
    await db.commit()
    return await get_question_by_id(db, question_id)


async def delete_question(db: AsyncSession, question_id: int) -> bool:
    question = await get_question_by_id(db, question_id)
    if not question:
        return False
    await db.delete(question)
    await db.commit()
    return True


async def get_all_question_groups(db: AsyncSession, active_only: bool = False) -> list[QuestionGroup]:
    query = select(QuestionGroup).options(selectinload(QuestionGroup.questions).selectinload(Question.groups))
    if active_only:
        query = query.where(QuestionGroup.is_active == True)
    result = await db.execute(query.order_by(QuestionGroup.name.asc()))
    return result.scalars().all()


async def get_question_group_by_id(db: AsyncSession, group_id: int) -> QuestionGroup | None:
    result = await db.execute(
        select(QuestionGroup).options(
            selectinload(QuestionGroup.questions).selectinload(Question.groups)
        ).where(QuestionGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def create_question_group(db: AsyncSession, **kwargs) -> QuestionGroup:
    group = QuestionGroup(**kwargs)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return await get_question_group_by_id(db, group.id)


async def update_question_group(db: AsyncSession, group_id: int, **kwargs) -> QuestionGroup | None:
    group = await get_question_group_by_id(db, group_id)
    if not group:
        return None
    for field, value in kwargs.items():
        setattr(group, field, value)
    await db.commit()
    return await get_question_group_by_id(db, group_id)


async def delete_question_group(db: AsyncSession, group_id: int) -> bool:
    group = await get_question_group_by_id(db, group_id)
    if not group:
        return False
    orphan_questions = [
        question for question in group.questions
        if len(question.groups) == 1 and question.groups[0].id == group_id
    ]
    for question in orphan_questions:
        await db.delete(question)
    await db.delete(group)
    await db.commit()
    return True


async def get_active_question_groups_with_questions(db: AsyncSession, language: str) -> list[QuestionGroup]:
    result = await db.execute(
        select(QuestionGroup)
        .join(QuestionGroup.questions)
        .options(
            selectinload(QuestionGroup.questions).selectinload(Question.choices),
            selectinload(QuestionGroup.questions).selectinload(Question.groups),
        )
        .where(
            QuestionGroup.is_active == True,
            Question.is_active == True,
            Question.language == language,
        )
        .distinct()
    )
    groups = result.scalars().all()
    filtered_groups = []
    for group in groups:
        group.questions = [
            question for question in group.questions
            if question.is_active and question.language == language
        ]
        if group.questions:
            filtered_groups.append(group)
    return filtered_groups


# --- QuestionChoice CRUD ---

async def create_choice(db: AsyncSession, **kwargs) -> QuestionChoice:
    choice = QuestionChoice(**kwargs)
    db.add(choice)
    await db.commit()
    await db.refresh(choice)
    return choice


async def get_choice_by_id(db: AsyncSession, choice_id: int) -> QuestionChoice | None:
    result = await db.execute(select(QuestionChoice).where(QuestionChoice.id == choice_id))
    return result.scalar_one_or_none()


async def update_choice(db: AsyncSession, choice_id: int, **kwargs) -> QuestionChoice | None:
    choice = await get_choice_by_id(db, choice_id)
    if not choice:
        return None
    for field, value in kwargs.items():
        setattr(choice, field, value)
    await db.commit()
    await db.refresh(choice)
    return choice


async def delete_choice(db: AsyncSession, choice_id: int) -> bool:
    choice = await get_choice_by_id(db, choice_id)
    if not choice:
        return False
    await db.delete(choice)
    await db.commit()
    return True


# --- Ingredient CRUD ---

async def get_all_ingredients(
    db: AsyncSession,
    language: str | None = None,
    type: str | None = None,
    category: str | None = None,
    active_only: bool = True,
) -> list[Ingredient]:
    query = select(Ingredient)
    if active_only:
        query = query.where(Ingredient.is_active == True)
    if language:
        query = query.where(Ingredient.language == language)
    if type:
        query = query.where(Ingredient.type == type)
    if category:
        query = query.where(Ingredient.category == category)
    result = await db.execute(query)
    return result.scalars().all()


async def get_ingredient_by_id(db: AsyncSession, ingredient_id: int) -> Ingredient | None:
    result = await db.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    return result.scalar_one_or_none()


async def create_ingredient(db: AsyncSession, **kwargs) -> Ingredient:
    ingredient = Ingredient(**kwargs)
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


async def update_ingredient(db: AsyncSession, ingredient_id: int, **kwargs) -> Ingredient | None:
    ingredient = await get_ingredient_by_id(db, ingredient_id)
    if not ingredient:
        return None
    for field, value in kwargs.items():
        setattr(ingredient, field, value)
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


async def delete_ingredient(db: AsyncSession, ingredient_id: int) -> bool:
    ingredient = await get_ingredient_by_id(db, ingredient_id)
    if not ingredient:
        return False
    await db.delete(ingredient)
    await db.commit()
    return True
