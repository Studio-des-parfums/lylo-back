from datetime import date as date_type, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Customer, GeneratedFormula, Printer, TeamMember


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
