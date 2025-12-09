# app/repositories/likes_repository.py

from __future__ import annotations

from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AnimalLike, Animal, User


async def list_outgoing_likes(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[AnimalLike]:
    stmt = (
        select(AnimalLike)
        .options(
            selectinload(AnimalLike.animal).selectinload(Animal.photos),
        )
        .where(
            and_(
                AnimalLike.from_user_id == user_id,
                AnimalLike.result == "like",
            )
        )
        .order_by(AnimalLike.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_incoming_likes(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[AnimalLike]:
    """
    Лайки на животных пользователя user_id.
    """
    stmt = (
        select(AnimalLike)
        .options(
            selectinload(AnimalLike.animal).selectinload(Animal.photos),
            selectinload(AnimalLike.from_user),
        )
        .where(
            and_(
                AnimalLike.result == "like",
                AnimalLike.animal_id.in_(
                    select(Animal.id).where(Animal.owner_user_id == user_id)
                ),
            )
        )
        .order_by(AnimalLike.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
