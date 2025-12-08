from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


_settings = get_settings()

DATABASE_URL: str = _settings.database_url
ECHO_SQL: bool = _settings.debug

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=ECHO_SQL,
)

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Предоставляет AsyncSession через Depends.
    """
    async with SessionFactory() as session:
        yield session
