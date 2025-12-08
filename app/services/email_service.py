from __future__ import annotations

from email.message import EmailMessage
import logging

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


async def send_email_verification_code(to_email: str, code: str) -> None:
    """
    Отправляет на почту одноразовый код подтверждения регистрации.
    """
    message = EmailMessage()
    message["Subject"] = "Pature: код подтверждения"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email

    body = (
        f"Ваш код подтверждения регистрации в Pature: {code}\n\n"
        f"Код действителен {settings.email_verification_code_ttl_minutes} минут."
    )
    message.set_content(body)

    try:
        logger.info(
            "Отправляет код подтверждения на %s через %s:%s (start_tls=%s, use_tls=%s)",
            to_email,
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_start_tls,
            settings.smtp_use_tls,
        )
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            start_tls=settings.smtp_start_tls,
        )
        logger.info("Письмо с кодом подтверждения успешно отправлено")
    except Exception as exc:
        logger.exception("Не удалось отправить письмо с кодом подтверждения: %s", exc)
        # важно: пробрасывает дальше, чтобы /auth/register вернул 500 и вы не потеряли стек
        raise
