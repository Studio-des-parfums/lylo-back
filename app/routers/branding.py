from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database import crud
from app.services import s3_service

router = APIRouter(prefix="/branding", tags=["branding"])


class BrandingResponse(BaseModel):
    logo_url: str | None


@router.get("", response_model=BrandingResponse)
async def get_branding(db: AsyncSession = Depends(get_db)):
    logo = await crud.get_project_logo(db)
    return BrandingResponse(logo_url=logo.image_url if logo else None)


@router.post("/logo", response_model=BrandingResponse)
async def upload_logo(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    allowed = {"image/", "application/octet-stream"}
    if file.content_type and not any(file.content_type.startswith(p) for p in allowed):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Le fichier est vide")

    existing = await crud.get_project_logo(db)
    if existing:
        s3_service.delete_project_logo(existing.image_url)

    try:
        image_url = s3_service.upload_project_logo(file_bytes, file.filename, file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logo = await crud.set_project_logo(db, image_url)
    return BrandingResponse(logo_url=logo.image_url)


@router.delete("/logo", status_code=204)
async def delete_logo(db: AsyncSession = Depends(get_db)):
    logo = await crud.delete_project_logo(db)
    if logo:
        s3_service.delete_project_logo(logo.image_url)
