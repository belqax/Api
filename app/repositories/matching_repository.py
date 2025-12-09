# app/repositories/matching_repository.py

from __future__ import annotations

from typing import Optional, Tuple, List

from sqlalchemy import select, and_, exists, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Animal,
    AnimalLike,
    UserMatch,
    User,
)


async def create_or_update_like(
    db: AsyncSession,
    *,
    from_user_id: int,
    animal_id: int,
    result: str,
) -> AnimalLike:
    if result not in ("like", "dislike"):
        raise ValueError("result must be 'like' or 'dislike'")

    stmt = select(AnimalLike).where(
        AnimalLike.from_user_id == from_user_id,
        AnimalLike.animal_id == animal_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None:
        like = AnimalLike(
            from_user_id=from_user_id,
            animal_id=animal_id,
            result=result,
        )
        db.add(like)
        await db.commit()
        await db.refresh(like)
        return like

    existing.result = result
    await db.commit()
    await db.refresh(existing)
    return existing


async def _normalize_match_pair(
    user_a_id: int,
    user_b_id: int,
) -> tuple[int, int]:
    if user_a_id == user_b_id:
        raise ValueError("Match between the same user is not allowed")
    return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)


async def get_or_create_match(
    db: AsyncSession,
    *,
    user_a_id: int,
    user_b_id: int,
) -> Tuple[UserMatch, bool]:
    user_id1, user_id2 = await _normalize_match_pair(user_a_id, user_b_id)

    stmt = select(UserMatch).where(
        UserMatch.user_id1 == user_id1,
        UserMatch.user_id2 == user_id2,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing, False

    match = UserMatch(
        user_id1=user_id1,
        user_id2=user_id2,
    )
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return match, True


async def detect_mutual_like_and_create_match(
    db: AsyncSession,
    *,
    from_user_id: int,
    target_animal_id: int,
) -> Tuple[Optional[UserMatch], bool]:
    """
    Проверяет, привёл ли лайк к взаимному матчу.
    Возвращает (match, created_flag).
    """
    # Находит владельца животного
    stmt_animal = select(Animal).where(Animal.id == target_animal_id)
    animal = (await db.execute(stmt_animal)).scalar_one_or_none()
    if animal is None:
        return None, False

    target_user_id = animal.owner_user_id
    if target_user_id == from_user_id:
        return None, False

    # Проверяет, лайкал ли владелец target_user_id животных from_user_id
    mutual_like_exists_stmt = select(
        exists().where(
            and_(
                AnimalLike.from_user_id == target_user_id,
                AnimalLike.result == "like",
                AnimalLike.animal_id.in_(
                    select(Animal.id).where(Animal.owner_user_id == from_user_id)
                ),
            )
        )
    )

    mutual_like_exists = (await db.execute(mutual_like_exists_stmt)).scalar_one()
    if not mutual_like_exists:
        return None, False

    match, created = await get_or_create_match(
        db,
        user_a_id=from_user_id,
        user_b_id=target_user_id,
    )
    return match, created


async def list_matches_for_user(
    db: AsyncSession,
    *,
    user_id: int,
) -> List[UserMatch]:
    stmt = (
        select(UserMatch)
        .options(
            selectinload(UserMatch.user1).selectinload(User.profile),
            selectinload(UserMatch.user2).selectinload(User.profile),
        )
        .where(
            or_(
                UserMatch.user_id1 == user_id,
                UserMatch.user_id2 == user_id,
            )
        )
        .order_by(UserMatch.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
