# app/services/rate_limiter.py
from __future__ import annotations

import datetime as dt
from typing import Any, Type

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def enforce_code_send_limits(
    db: AsyncSession,
    *,
    model: Type[Any],
    user_id: int,
    target_value: str,
    purpose: str,
    now: dt.datetime,
    cooldown_seconds: int,
    max_per_hour: int,
    channel: str,
    target_field: str,
) -> None:
    """
    Применяет два ограничения для отправки кодов (email/SMS):
    1) не чаще, чем раз в cooldown_seconds;
    2) не более max_per_hour отправок за последний час.

    Аргументы:
    - db: AsyncSession
    - model: SQLAlchemy-модель кода (EmailVerificationCode, PhoneVerificationCode и т.п.)
    - user_id: идентификатор пользователя
    - target_value: e-mail или телефон
    - purpose: назначение кода ("register", "verify_phone" и т.п.)
    - now: текущее время в UTC
    - cooldown_seconds: пауза между отправками
    - max_per_hour: максимум отправок за последний час
    - channel: строка "email" или "sms" для формирования кодов ошибок
    - target_field: имя поля модели, в котором хранится e-mail/phone
    """
    target_column = getattr(model, target_field)

    # 1) Пауза между отправками: ищет последний код
    stmt_last = (
        select(model)
        .where(
            model.user_id == user_id,
            target_column == target_value,
            model.purpose == purpose,
        )
        .order_by(model.created_at.desc())
        .limit(1)
    )
    result_last = await db.execute(stmt_last)
    last_code = result_last.scalar_one_or_none()

    if last_code is not None:
        elapsed = (now - last_code.created_at).total_seconds()
        if elapsed < cooldown_seconds:
            retry_after_seconds = int(cooldown_seconds - elapsed)
            retry_after_at = last_code.created_at + dt.timedelta(
                seconds=cooldown_seconds
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": f"{channel}_resend_cooldown",
                    "message": "Too many requests. Please wait before requesting a new code.",
                    "retry_after_seconds": retry_after_seconds,
                },
            )

    # 2) Лимит на количество отправок за час
    one_hour_ago = now - dt.timedelta(hours=1)

    stmt_hour = (
        select(model)
        .where(
            model.user_id == user_id,
            target_column == target_value,
            model.purpose == purpose,
            model.created_at >= one_hour_ago,
        )
    )
    result_hour = await db.execute(stmt_hour)
    codes_last_hour = result_hour.scalars().all()
    sent_last_hour = len(codes_last_hour)

    if sent_last_hour >= max_per_hour and codes_last_hour:
        oldest_in_window = min(codes_last_hour, key=lambda c: c.created_at)
        next_allowed_at = oldest_in_window.created_at + dt.timedelta(hours=1)
        retry_after_seconds = max(
            0, int((next_allowed_at - now).total_seconds())
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": f"{channel}_resend_hourly_limit",
                "message": "Limit for verification messages exceeded.",
                "retry_after_seconds": retry_after_seconds,
            },
        )
