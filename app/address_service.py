# app/address_service.py

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.schemas import (
    AddressSuggestion,
    AddressAutocompleteResponse,
    ReverseGeocodeResponse,
    AddressSearchResponse,
)

logger = logging.getLogger(__name__)

settings = get_settings()

GEOAPIFY_AUTOCOMPLETE_URL: str = settings.geoapify_base_url
GEOAPIFY_REVERSE_URL: str = settings.geoapify_reverse_url
GEOAPIFY_SEARCH_URL: str = settings.geoapify_search_url
GEOAPIFY_API_KEY: Optional[str] = settings.geoapify_api_key
GEOAPIFY_DEFAULT_LANG: str = settings.geoapify_default_lang
GEOAPIFY_DEFAULT_LIMIT: int = settings.geoapify_default_limit


def _build_suggestion_from_properties(properties: dict) -> Optional[AddressSuggestion]:
    formatted = properties.get("formatted") or ""
    if not formatted:
        return None

    lat = properties.get("lat")
    lon = properties.get("lon")
    if lat is None or lon is None:
        return None

    rank = properties.get("rank") or {}
    timezone = properties.get("timezone") or {}

    suggestion = AddressSuggestion(
        formatted=formatted,
        lat=float(lat),
        lon=float(lon),
        country=properties.get("country"),
        state=properties.get("state"),
        region=properties.get("region"),
        county=properties.get("county"),
        city=properties.get("city"),
        district=properties.get("district"),
        neighbourhood=properties.get("neighbourhood"),
        postcode=properties.get("postcode"),
        street=properties.get("street"),
        housenumber=properties.get("housenumber"),
        plus_code=properties.get("plus_code"),
        timezone=timezone.get("name"),
        result_type=properties.get("result_type"),
        confidence=float(rank.get("confidence")) if rank.get("confidence") is not None else None,
    )
    return suggestion


def _parse_features_to_suggestions(features: List[dict]) -> List[AddressSuggestion]:
    suggestions: List[AddressSuggestion] = []
    for feature in features:
        properties: dict = feature.get("properties") or {}
        suggestion = _build_suggestion_from_properties(properties)
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions


def _parse_results_array_to_suggestions(results: List[dict]) -> List[AddressSuggestion]:
    suggestions: List[AddressSuggestion] = []
    for item in results:
        properties = dict(item)
        suggestion = _build_suggestion_from_properties(properties)
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions


async def autocomplete_address(
    text: str,
    *,
    limit: int | None = None,
    lang: str | None = None,
    type_: str | None = None,
) -> AddressAutocompleteResponse:
    if not GEOAPIFY_API_KEY:
        logger.error("Geoapify API key is not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding service is not configured",
        )

    normalized_text = text.strip()
    if not normalized_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text must not be empty",
        )

    params: Dict[str, Any] = {
        "text": normalized_text,
        "apiKey": GEOAPIFY_API_KEY,
        "lang": lang or GEOAPIFY_DEFAULT_LANG,
        "limit": limit or GEOAPIFY_DEFAULT_LIMIT,
    }

    if type_:
        params["type"] = type_

    logger.info(
        "Запрашивает автодополнение адреса в Geoapify: text=%r, limit=%s, lang=%s, type=%s",
        normalized_text,
        params["limit"],
        params["lang"],
        type_,
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GEOAPIFY_AUTOCOMPLETE_URL, params=params)
    except httpx.RequestError as exc:
        logger.exception("Ошибка сети при запросе к Geoapify (autocomplete)")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach geocoding service: {exc}",
        )

    if response.status_code >= 500:
        logger.error(
            "Geoapify (autocomplete) вернул ошибку %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Geocoding service is temporarily unavailable",
        )

    if response.status_code >= 400:
        logger.warning(
            "Geoapify (autocomplete) вернул клиентскую ошибку %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid geocoding request",
        )

    try:
        payload = response.json()
    except ValueError:
        logger.error("Geoapify (autocomplete) вернул некорректный JSON: %s", response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from geocoding service",
        )

    features: List[dict] = payload.get("features") or []
    suggestions = _parse_features_to_suggestions(features)

    return AddressAutocompleteResponse(
        query_text=normalized_text,
        suggestions=suggestions,
    )


async def reverse_geocode(
    lat: float,
    lon: float,
    *,
    lang: str | None = None,
) -> ReverseGeocodeResponse:
    if not GEOAPIFY_API_KEY:
        logger.error("Geoapify API key is not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding service is not configured",
        )

    params: Dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "apiKey": GEOAPIFY_API_KEY,
        "lang": lang or GEOAPIFY_DEFAULT_LANG,
        "format": "json",
    }

    logger.info(
        "Запрашивает reverse-geocoding в Geoapify: lat=%s, lon=%s, lang=%s",
        lat,
        lon,
        params["lang"],
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GEOAPIFY_REVERSE_URL, params=params)
    except httpx.RequestError as exc:
        logger.exception("Ошибка сети при запросе к Geoapify (reverse)")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach geocoding service: {exc}",
        )

    if response.status_code >= 500:
        logger.error(
            "Geoapify (reverse) вернул ошибку %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Geocoding service is temporarily unavailable",
        )

    if response.status_code >= 400:
        logger.warning(
            "Geoapify (reverse) вернул клиентскую ошибку %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid geocoding request",
        )

    try:
        payload = response.json()
    except ValueError:
        logger.error("Geoapify (reverse) вернул некорректный JSON: %s", response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from geocoding service",
        )

    results: List[dict] = payload.get("results") or []
    suggestions = _parse_results_array_to_suggestions(results)

    return ReverseGeocodeResponse(
        query_lat=lat,
        query_lon=lon,
        results=suggestions,
    )


async def search_address(
    text: str,
    *,
    limit: int | None = None,
    lang: str | None = None,
) -> AddressSearchResponse:
    if not GEOAPIFY_API_KEY:
        logger.error("Geoapify API key is not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding service is not configured",
        )

    normalized_text = text.strip()
    if not normalized_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text must not be empty",
        )

    params: Dict[str, Any] = {
        "text": normalized_text,
        "apiKey": GEOAPIFY_API_KEY,
        "lang": lang or GEOAPIFY_DEFAULT_LANG,
        "limit": limit or GEOAPIFY_DEFAULT_LIMIT,
        "format": "json",
    }

    logger.info(
        "Запрашивает поисковый геокодинг в Geoapify: text=%r, limit=%s, lang=%s",
        normalized_text,
        params["limit"],
        params["lang"],
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GEOAPIFY_SEARCH_URL, params=params)
    except httpx.RequestError as exc:
        logger.exception("Ошибка сети при запросе к Geoapify (search)")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach geocoding service: {exc}",
        )

    if response.status_code >= 500:
        logger.error(
            "Geoapify (search) вернул ошибку %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Geocoding service is temporarily unavailable",
        )

    if response.status_code >= 400:
        logger.warning(
            "Geoapify (search) вернул клиентскую ошибку %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid geocoding request",
        )

    try:
        payload = response.json()
    except ValueError:
        logger.error("Geoapify (search) вернул некорректный JSON: %s", response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from geocoding service",
        )

    results: List[dict] = payload.get("results") or []
    suggestions = _parse_results_array_to_suggestions(results)

    return AddressSearchResponse(
        query_text=normalized_text,
        results=suggestions,
    )
