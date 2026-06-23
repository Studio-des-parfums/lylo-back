from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database import crud

router = APIRouter(prefix="/participants", tags=["participants"])


class ParticipantCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None


class ParticipantResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ParticipantResponse])
async def list_participants(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_participants(db)


@router.get("/{participant_id}", response_model=ParticipantResponse)
async def get_participant(participant_id: int, db: AsyncSession = Depends(get_db)):
    participant = await crud.get_participant_by_id(db, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant introuvable")
    return participant


@router.post("/", response_model=ParticipantResponse, status_code=201)
async def create_participant(body: ParticipantCreate, db: AsyncSession = Depends(get_db)):
    return await crud.upsert_participant(db, **body.model_dump(exclude_none=True))
