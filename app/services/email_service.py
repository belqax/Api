import ssl
from email.message import EmailMessage
import aiosmtplib

from app.config import get_settings
from app.core.logging import logger  # если у тебя свой логгер

settings = get_settings()


async def send_email_verification_code(to_email: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Pature: код подтверждения"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email

    body = (
        f"Ваш код подтверждения регистрации в Pature: {code}\n\n"
        f"Код действителен {settings.email_verification_code_ttl_minutes} минут."
    )
    message.set_content(body)

    # Создаёт TLS-контекст без проверки hostname (и при желании без проверки цепочки)
    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    # При необходимости можно ещё ослабить:
    # tls_context.verify_mode = ssl.CERT_NONE

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
            hostname=settings.smtp_host,   # здесь может быть 127.0.0.1
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            start_tls=settings.smtp_start_tls,
            tls_context=tls_context,
        )
        logger.info("Письмо с кодом подтверждения успешно отправлено")
    except Exception as exc:
        logger.exception("Не удалось отправить письмо с кодом подтверждения: %s", exc)
        raise
