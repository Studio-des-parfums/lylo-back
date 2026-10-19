from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import analytics_cache
from app.database.connection import get_db
from app.database import crud
from app.models.schemas import (
    AnalyticsSummaryResponse,
    FormulaCountResponse,
    FormulaTypesResponse,
    LanguagesResponse,
    ModesResponse,
    ProfilesResponse,
    TopNotesResponse,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/cache/clear")
async def clear_analytics_cache():
    """
    Effacer l'ensemble du cache mémoire TTLCache des analytics.
    """
    count = analytics_cache.size()
    analytics_cache.clear()
    return {
        "status": "ok",
        "message": f"Cache analytics invalidé ({count} entrées purgées)",
    }


@router.get("/formulas/count", response_model=FormulaCountResponse)
async def get_formulas_count(
    group_by: str = Query("day", pattern="^(day|month|year)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Nombre de formules générées groupées par jour, mois ou année, avec filtrage temporel optionnel.
    """
    return await crud.get_formula_counts(
        db=db,
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )


@router.get("/notes/top", response_model=TopNotesResponse)
async def get_top_notes(
    limit: int = Query(10, ge=1, le=100),
    category: str = Query("all", pattern="^(all|top|heart|base)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Notes olfactives les plus recommandées, globalement ou par pyramide (top, heart, base).
    """
    return await crud.get_top_notes(
        db=db,
        limit=limit,
        category=category,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )


@router.get("/profiles/top", response_model=ProfilesResponse)
async def get_top_profiles(
    limit: int = Query(10, ge=1, le=100),
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Profils de parfum les plus fréquemment recommandés.
    """
    return await crud.get_profile_stats(
        db=db,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )


@router.get("/languages", response_model=LanguagesResponse)
async def get_languages(
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Répartition des langues choisies lors de la création de formules.
    """
    return await crud.get_language_stats(
        db=db,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )


@router.get("/modes", response_model=ModesResponse)
async def get_modes(
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Pourcentage d'utilisation par mode d'interaction (quiz vs voice).
    """
    return await crud.get_mode_stats(
        db=db,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )


@router.get("/formula-types", response_model=FormulaTypesResponse)
async def get_formula_types(
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Pourcentage par type de formule (mix, frais, puissant, autre).
    """
    return await crud.get_formula_type_stats(
        db=db,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    nocache: bool = Query(False, description="Ignorer le cache et forcer le calcul direct"),
    db: AsyncSession = Depends(get_db),
):
    """
    Vue synthétique globale pour dashboard (KPIs consolidés).
    """
    return await crud.get_analytics_summary(
        db=db,
        date_from=date_from,
        date_to=date_to,
        bypass_cache=nocache,
    )
