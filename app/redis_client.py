# app/redis_client.py
from __future__ import annotations

import redis.asyncio as redis

from app.config import get_settings

_settings = get_settings()

redis_client: redis.Redis = redis.from_url(
    _settings.ip_rate_limit_redis_dsn,
    encoding="utf-8",
    decode_responses=True,
)
