from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=True)


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Предоставляет AsyncSession для одного HTTP-запроса.
    """
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Возвращает текущего активного пользователя по access-токену.
    Предзагружает profile, privacy_settings, settings.
    """
    token = credentials.credentials

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except ValueError:
        raise unauthorized

    if payload.get("type") != "access":
        raise unauthorized

    sub = payload.get("sub")
    if not sub:
        raise unauthorized

    try:
        user_id = int(sub)
    except ValueError:
        raise unauthorized

    stmt = (
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.privacy_settings),
            selectinload(User.settings),
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise unauthorized

    return user
