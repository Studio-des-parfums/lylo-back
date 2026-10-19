from collections import Counter
from datetime import date as date_type, datetime, time, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import analytics_cache
from app.database.models import GeneratedFormula


def _apply_date_filters(query, date_from: date_type | None, date_to: date_type | None):
    if date_from:
        start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        query = query.where(GeneratedFormula.created_at >= start_dt)
    if date_to:
        end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.where(GeneratedFormula.created_at < end_dt)
    return query


def _extract_note_name(item) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("note") or "").strip()
    if item is not None:
        return str(item).strip()
    return ""


async def get_formula_counts(
    db: AsyncSession,
    group_by: str = "day",
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    if group_by not in ("day", "month", "year"):
        group_by = "day"

    cache_key = f"counts:{group_by}:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    period_col = func.date_trunc(group_by, GeneratedFormula.created_at).label("period")
    query = (
        select(period_col, func.count(GeneratedFormula.id).label("count"))
        .where(GeneratedFormula.created_at.is_not(None))
    )
    query = _apply_date_filters(query, date_from, date_to)
    query = query.group_by(period_col).order_by(period_col.asc())

    rows = (await db.execute(query)).all()

    data = []
    total = 0
    for r in rows:
        period_dt = r.period
        if group_by == "day":
            period_str = period_dt.strftime("%Y-%m-%d")
        elif group_by == "month":
            period_str = period_dt.strftime("%Y-%m")
        else:
            period_str = period_dt.strftime("%Y")

        cnt = r.count
        total += cnt
        data.append({"period": period_str, "count": cnt})

    # Si aucune ligne mais date filters donnés ou pas de dates, vérifions le count exact
    if not data:
        count_query = _apply_date_filters(select(func.count(GeneratedFormula.id)), date_from, date_to)
        total = (await db.execute(count_query)).scalar() or 0

    result = {
        "total": total,
        "group_by": group_by,
        "date_from": date_from,
        "date_to": date_to,
        "data": data,
    }
    analytics_cache.set(cache_key, result)
    return result


async def get_top_notes(
    db: AsyncSession,
    limit: int = 10,
    category: str = "all",
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    cache_key = f"notes:{limit}:{category}:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    count_query = _apply_date_filters(select(func.count(GeneratedFormula.id)), date_from, date_to)
    total_formulas = (await db.execute(count_query)).scalar() or 0

    notes_query = _apply_date_filters(
        select(GeneratedFormula.top_notes, GeneratedFormula.heart_notes, GeneratedFormula.base_notes),
        date_from,
        date_to,
    )
    rows = (await db.execute(notes_query)).all()

    c = Counter()
    for row in rows:
        cols_to_check = []
        if category in ("all", "top"):
            cols_to_check.append(row.top_notes)
        if category in ("all", "heart"):
            cols_to_check.append(row.heart_notes)
        if category in ("all", "base"):
            cols_to_check.append(row.base_notes)

        for note_list in cols_to_check:
            if isinstance(note_list, list):
                for item in note_list:
                    name = _extract_note_name(item)
                    if name:
                        c[name] += 1

    data = []
    for note, count in c.most_common(limit):
        pct = round((count / total_formulas) * 100, 2) if total_formulas > 0 else 0.0
        data.append({
            "note": note,
            "category": category,
            "count": count,
            "percentage": pct,
        })

    result = {
        "total_formulas": total_formulas,
        "category": category,
        "limit": limit,
        "data": data,
    }
    analytics_cache.set(cache_key, result)
    return result


async def get_profile_stats(
    db: AsyncSession,
    limit: int = 10,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    cache_key = f"profiles:{limit}:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    total_query = select(func.count(GeneratedFormula.id)).where(GeneratedFormula.profile.is_not(None))
    total_query = _apply_date_filters(total_query, date_from, date_to)
    total = (await db.execute(total_query)).scalar() or 0

    query = (
        select(GeneratedFormula.profile, func.count(GeneratedFormula.id).label("count"))
        .where(GeneratedFormula.profile.is_not(None))
    )
    query = _apply_date_filters(query, date_from, date_to)
    query = query.group_by(GeneratedFormula.profile).order_by(func.count(GeneratedFormula.id).desc()).limit(limit)

    rows = (await db.execute(query)).all()

    data = []
    for r in rows:
        pct = round((r.count / total) * 100, 2) if total > 0 else 0.0
        data.append({
            "profile": r.profile,
            "count": r.count,
            "percentage": pct,
        })

    result = {
        "total": total,
        "data": data,
    }
    analytics_cache.set(cache_key, result)
    return result


async def get_language_stats(
    db: AsyncSession,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    cache_key = f"languages:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    total_query = _apply_date_filters(select(func.count(GeneratedFormula.id)), date_from, date_to)
    total = (await db.execute(total_query)).scalar() or 0

    lang_col = func.coalesce(GeneratedFormula.language, "inconnu").label("language")
    query = select(lang_col, func.count(GeneratedFormula.id).label("count")).select_from(GeneratedFormula)
    query = _apply_date_filters(query, date_from, date_to)
    query = query.group_by(lang_col).order_by(func.count(GeneratedFormula.id).desc())

    rows = (await db.execute(query)).all()

    data = []
    for r in rows:
        pct = round((r.count / total) * 100, 2) if total > 0 else 0.0
        data.append({
            "language": r.language,
            "count": r.count,
            "percentage": pct,
        })

    result = {
        "total": total,
        "data": data,
    }
    analytics_cache.set(cache_key, result)
    return result


async def get_mode_stats(
    db: AsyncSession,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    cache_key = f"modes:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    total_query = _apply_date_filters(select(func.count(GeneratedFormula.id)), date_from, date_to)
    total = (await db.execute(total_query)).scalar() or 0

    mode_expr = case(
        (GeneratedFormula.input_mode.is_(None), "quiz"),
        (func.lower(GeneratedFormula.input_mode).in_(["quiz"]), "quiz"),
        (func.lower(GeneratedFormula.input_mode).in_(["voice", "vocal"]), "voice"),
        else_=func.lower(GeneratedFormula.input_mode),
    ).label("mode")

    query = select(mode_expr, func.count(GeneratedFormula.id).label("count")).select_from(GeneratedFormula)
    query = _apply_date_filters(query, date_from, date_to)
    query = query.group_by(mode_expr).order_by(func.count(GeneratedFormula.id).desc())

    rows = (await db.execute(query)).all()

    data = []
    for r in rows:
        pct = round((r.count / total) * 100, 2) if total > 0 else 0.0
        data.append({
            "mode": r.mode,
            "count": r.count,
            "percentage": pct,
        })

    result = {
        "total": total,
        "data": data,
    }
    analytics_cache.set(cache_key, result)
    return result


async def get_formula_type_stats(
    db: AsyncSession,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    cache_key = f"formula_types:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    total_query = _apply_date_filters(select(func.count(GeneratedFormula.id)), date_from, date_to)
    total = (await db.execute(total_query)).scalar() or 0

    type_expr = case(
        (GeneratedFormula.formula_type.is_(None), "autre"),
        (func.trim(GeneratedFormula.formula_type) == "", "autre"),
        else_=func.lower(GeneratedFormula.formula_type),
    ).label("formula_type")

    query = select(type_expr, func.count(GeneratedFormula.id).label("count")).select_from(GeneratedFormula)
    query = _apply_date_filters(query, date_from, date_to)
    query = query.group_by(type_expr).order_by(func.count(GeneratedFormula.id).desc())

    rows = (await db.execute(query)).all()

    data = []
    for r in rows:
        pct = round((r.count / total) * 100, 2) if total > 0 else 0.0
        data.append({
            "formula_type": r.formula_type,
            "count": r.count,
            "percentage": pct,
        })

    result = {
        "total": total,
        "data": data,
    }
    analytics_cache.set(cache_key, result)
    return result


async def get_analytics_summary(
    db: AsyncSession,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    bypass_cache: bool = False,
) -> dict:
    cache_key = f"summary:{date_from}:{date_to}"
    if not bypass_cache:
        cached = analytics_cache.get(cache_key)
        if cached is not None:
            return cached

    total_query = _apply_date_filters(select(func.count(GeneratedFormula.id)), date_from, date_to)
    total_formulas = (await db.execute(total_query)).scalar() or 0

    profiles_res = await get_profile_stats(db, limit=5, date_from=date_from, date_to=date_to, bypass_cache=bypass_cache)
    modes_res = await get_mode_stats(db, date_from=date_from, date_to=date_to, bypass_cache=bypass_cache)
    top_notes_res = await get_top_notes(db, limit=5, category="all", date_from=date_from, date_to=date_to, bypass_cache=bypass_cache)
    formula_types_res = await get_formula_type_stats(db, date_from=date_from, date_to=date_to, bypass_cache=bypass_cache)
    languages_res = await get_language_stats(db, date_from=date_from, date_to=date_to, bypass_cache=bypass_cache)

    result = {
        "total_formulas": total_formulas,
        "profiles": profiles_res["data"],
        "modes": modes_res["data"],
        "top_notes": top_notes_res["data"],
        "formula_types": formula_types_res["data"],
        "languages": languages_res["data"],
    }
    analytics_cache.set(cache_key, result)
    return result
