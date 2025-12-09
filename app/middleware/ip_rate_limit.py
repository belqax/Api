# app/middleware/ip_rate_limit.py
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.redis_client import redis_client

settings = get_settings()


def _get_client_ip(request: Request) -> str:
    # Если стоишь за Nginx/Cloudflare, в nginx надо прокидывать X-Real-IP.
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.requests_per_minute = settings.ip_rate_limit_requests_per_minute
        self.block_ttl = settings.ip_rate_limit_block_ttl_seconds

    async def dispatch(self, request: Request, call_next):
        ip = _get_client_ip(request)

        # Ключи в Redis
        now = dt.datetime.utcnow()
        minute_bucket = now.strftime("%Y%m%d%H%M")
        counter_key = f"iprl:{ip}:{minute_bucket}"
        block_key = f"iprl:block:{ip}"

        # Проверяет, не заблокирован ли IP
        is_blocked = await redis_client.get(block_key)
        if is_blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "ip_blocked",
                    "message": "Too many requests from this IP. Try later.",
                },
            )

        # Увеличивает счётчик запросов в текущую минуту
        current_count = await redis_client.incr(counter_key)
        if current_count == 1:
            # устанавливает TTL, чтобы ключ сам умер
            await redis_client.expire(counter_key, 65)

        if current_count > self.requests_per_minute:
            # ставит блокировку IP
            await redis_client.set(block_key, "1", ex=self.block_ttl)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "ip_rate_limit_exceeded",
                    "message": "Too many requests from this IP. Try later.",
                },
            )

        response = await call_next(request)
        return response
