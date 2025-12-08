import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import engine
from app.models import Base
from app.routers import auth, profile, animals

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # позже сузишь под конкретные домены / схемы
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    # при наличии Alembic в проде использовать только миграции
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    os.makedirs(settings.media_root, exist_ok=True)


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(animals.router)
