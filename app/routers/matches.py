# app/routers/matches.py

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import MatchListItem, MatchUserSummary, UserBase, UserProfile
from app.repositories.matching_repository import list_matches_for_user

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=List[MatchListItem])
async def list_my_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MatchListItem]:
    matches = await list_matches_for_user(
        db,
        user_id=current_user.id,
    )

    items: list[MatchListItem] = []

    for m in matches:
        if m.user_id1 == current_user.id:
            counterpart = m.user2
        else:
            counterpart = m.user1

        # counterpart.profile уже подгружен через selectinload
        base = UserBase.model_validate(counterpart)
        profile = UserProfile.model_validate(counterpart.profile)

        items.append(
            MatchListItem(
                id=m.id,
                counterpart=MatchUserSummary(
                    user=base,
                    profile=profile,
                ),
                created_at=m.created_at,
            )
        )

    return items
