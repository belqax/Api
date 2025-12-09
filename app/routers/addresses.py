# app/routers/addresses.py

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import (
    AddressAutocompleteResponse,
    ReverseGeocodeResponse,
    AddressSearchResponse,
)
from app.address_service import (
    autocomplete_address,
    reverse_geocode,
    search_address,
)

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get(
    "/autocomplete",
    response_model=AddressAutocompleteResponse,
)
async def autocomplete_address_endpoint(
    text: str = Query(..., min_length=3, max_length=256),
    limit: int | None = Query(None, ge=1, le=20),
    lang: str | None = Query(None, min_length=2, max_length=5),
    type_: str | None = Query(
        None,
        alias="type",
        description="Опциональный тип объекта Geoapify (building, amenity и т.п.)",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressAutocompleteResponse:
    return await autocomplete_address(
        text=text,
        limit=limit,
        lang=lang,
        type_=type_,
    )


@router.get(
    "/reverse",
    response_model=ReverseGeocodeResponse,
)
async def reverse_geocode_endpoint(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    lang: str | None = Query(None, min_length=2, max_length=5),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReverseGeocodeResponse:
    return await reverse_geocode(
        lat=lat,
        lon=lon,
        lang=lang,
    )


@router.get(
    "/search",
    response_model=AddressSearchResponse,
)
async def search_address_endpoint(
    text: str = Query(..., min_length=2, max_length=256),
    limit: int | None = Query(None, ge=1, le=20),
    lang: str | None = Query(None, min_length=2, max_length=5),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressSearchResponse:
    return await search_address(
        text=text,
        limit=limit,
        lang=lang,
    )
