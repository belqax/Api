# app/utils/validators.py
from __future__ import annotations

import re
from typing import Final

from fastapi import HTTPException, status


PASSWORD_MIN_LENGTH: Final[int] = 8


def normalize_ru_phone(raw_phone: str) -> str:
    """
    Нормализует и валидирует российский номер телефона.

    Принимает:
    - +7XXXXXXXXXX
    - 7XXXXXXXXXX
    - 8XXXXXXXXXX
    - 10 цифр (без кода страны)

    Возвращает в формате: +7XXXXXXXXXX.
    """
    if raw_phone is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required",
        )

    raw_phone = raw_phone.strip()
    if not raw_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is empty",
        )

    digits = re.sub(r"\D", "", raw_phone)

    # 10 цифр → добавляет '7' как код страны
    if len(digits) == 10:
        digits = "7" + digits

    # Ожидает 11 цифр
    if len(digits) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Russian phone number must contain 10 or 11 digits",
        )

    # 8XXXXXXXXXX → 7XXXXXXXXXX
    if digits[0] == "8":
        digits = "7" + digits[1:]

    if digits[0] != "7":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Russian phone number must start with +7",
        )

    # Финальный формат: +7XXXXXXXXXX
    return "+7" + digits[1:]


def validate_password_strength(password: str) -> None:
    """
    Проверяет сложность пароля:
    - длина не менее PASSWORD_MIN_LENGTH;
    - есть хотя бы одна цифра;
    - есть хотя бы одна строчная буква;
    - есть хотя бы одна заглавная буква;
    - есть хотя бы один спецсимвол (не буква и не цифра).

    При нарушении выбрасывает HTTPException 400.
    """
    if password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required",
        )

    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters long",
        )

    has_digit = any(ch.isdigit() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_upper = any(ch.isupper() for ch in password)
    has_special = any(not ch.isalnum() for ch in password)

    if not has_digit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit",
        )

    if not has_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter",
        )

    if not has_upper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter",
        )

    if not has_special:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character",
        )
