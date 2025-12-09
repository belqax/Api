# app/routers/likes.py

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import (
    OutgoingLikeItem,
    IncomingLikeItem,
    AnimalWithPhotos,
    UserBase,
)
from app.repositories.likes_repository import (
    list_outgoing_likes,
    list_incoming_likes,
)

router = APIRouter(prefix="/likes", tags=["likes"])


@router.get(
    "/outgoing",
    response_model=List[OutgoingLikeItem],
    summary="List animals I liked",
)
async def get_outgoing_likes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[OutgoingLikeItem]:
    likes = await list_outgoing_likes(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    items: list[OutgoingLikeItem] = []
    for like in likes:
        animal_schema = AnimalWithPhotos.model_validate(like.animal)
        items.append(
            OutgoingLikeItem(
                id=like.id,
                animal=animal_schema,
                created_at=like.created_at,
            )
        )

    return items


@router.get(
    "/incoming",
    response_model=List[IncomingLikeItem],
    summary="List likes to my animals",
)
async def get_incoming_likes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[IncomingLikeItem]:
    likes = await list_incoming_likes(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    items: list[IncomingLikeItem] = []
    for like in likes:
        from_user = like.from_user
        from_user_schema = UserBase.model_validate(from_user)
        animal_schema = AnimalWithPhotos.model_validate(like.animal)

        items.append(
            IncomingLikeItem(
                id=like.id,
                from_user=from_user_schema,
                animal=animal_schema,
                created_at=like.created_at,
            )
        )

    return items
