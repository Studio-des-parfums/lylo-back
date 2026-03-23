import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.database.connection import engine
from app.routers import mail, sessions, customers, teams, lookup, ping

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_DB_KEEPALIVE_INTERVAL = 3600  # 1 heure


async def _db_keepalive():
    while True:
        await asyncio.sleep(_DB_KEEPALIVE_INTERVAL)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            print(f"[keepalive] DB ping failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_db_keepalive())
    yield
    task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Lilo Backend", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions.router)
    app.include_router(mail.router)
    app.include_router(customers.router)
    app.include_router(teams.router)
    app.include_router(lookup.router)
    app.include_router(ping.router)
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    return app
