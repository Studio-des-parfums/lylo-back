from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db

router = APIRouter(prefix="/api", tags=["ping"])

_SPEEDTEST_SIZE = 524288  # 512 KB
_SPEEDTEST_PAYLOAD = bytes(_SPEEDTEST_SIZE)


@router.get("/ping")
async def ping(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return Response(status_code=200)


@router.get("/speedtest")
async def speedtest():
    return Response(
        content=_SPEEDTEST_PAYLOAD,
        media_type="application/octet-stream",
        headers={"Content-Length": str(_SPEEDTEST_SIZE)},
    )
