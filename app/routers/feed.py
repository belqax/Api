# app/routers/feed.py

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import AnimalWithPhotos
from app.repositories.animal_repository import list_feed_animals

router = APIRouter(prefix="", tags=["feed"])


@router.get("/feed", response_model=List[AnimalWithPhotos])
async def get_feed(
    species: str | None = None,
    city: str | None = None,
    sex: str | None = None,
    age_from_years: int | None = Query(None, ge=0, le=50),
    age_to_years: int | None = Query(None, ge=0, le=50),
    has_photos: bool | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AnimalWithPhotos]:
    animals = await list_feed_animals(
        db,
        current_user_id=current_user.id,
        species=species,
        city=city,
        sex=sex,
        age_from_years=age_from_years,
        age_to_years=age_to_years,
        has_photos=has_photos,
        status="active",
        limit=limit,
        offset=offset,
    )
    return [AnimalWithPhotos.model_validate(a) for a in animals]
