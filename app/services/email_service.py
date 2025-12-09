import logging
import ssl
from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


async def send_email_verification_code(to_email: str, code: str) -> None:
    """
    Отправляет письмо с кодом подтверждения регистрации.
    Формирует multipart/alternative: текст + HTML.
    """
    subject = "Pature · Код подтверждения"

    text_body = (
        "Здравствуйте!\n\n"
        f"Ваш код подтверждения регистрации в Pature:\n\n"
        f"    {code}\n\n"
        f"Код действителен в течение {settings.email_verification_code_ttl_minutes} минут.\n\n"
        "Если вы не запрашивали регистрацию в Pature, просто игнорируйте это письмо.\n\n"
        "С уважением,\n"
        "команда Pature"
    )

    html_body = f"""\
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Код подтверждения регистрации</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center" style="padding:24px 16px;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:480px;background-color:#ffffff;border-radius:12px;box-shadow:0 4px 16px rgba(15,23,42,0.08);overflow:hidden;">
                    <tr>
                        <td style="padding:20px 24px 16px 24px;border-bottom:1px solid #eef1f7;">
                            <div style="font-size:18px;font-weight:600;color:#111827;">Pature</div>
                            <div style="margin-top:4px;font-size:14px;color:#6b7280;">Код подтверждения регистрации</div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 24px 8px 24px;font-size:14px;color:#111827;line-height:1.6;">
                            <p style="margin:0 0 12px 0;">Здравствуйте!</p>
                            <p style="margin:0 0 12px 0;">
                                Для подтверждения регистрации в сервисе Pature используйте следующий код:
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding:8px 24px 16px 24px;">
                            <div style="
                                display:inline-block;
                                padding:12px 24px;
                                border-radius:999px;
                                background:linear-gradient(135deg,#4f46e5,#6366f1);
                                color:#ffffff;
                                font-size:20px;
                                font-weight:700;
                                letter-spacing:0.20em;
                                text-align:center;
                            ">
                                {code}
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:0 24px 16px 24px;font-size:13px;color:#4b5563;line-height:1.6;">
                            <p style="margin:0 0 8px 0;">
                                Код действителен в течение <strong>{settings.email_verification_code_ttl_minutes} минут</strong>.
                            </p>
                            <p style="margin:0 0 8px 0;">
                                По истечении этого времени вам потребуется запросить новый код.
                            </p>
                            <p style="margin:8px 0 0 0;">
                                Если вы не запрашивали регистрацию в Pature, просто проигнорируйте это письмо.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:8px 24px 20px 24px;font-size:12px;color:#9ca3af;border-top:1px solid #eef1f7;">
                            <p style="margin:8px 0 0 0;">
                                С уважением,<br>
                                команда Pature
                            </p>
                        </td>
                    </tr>
                </table>
                <div style="margin-top:12px;font-size:11px;color:#9ca3af;max-width:480px;">
                    Вы получили это письмо, потому что указали данный адрес электронной почты при регистрации в Pature.
                </div>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email

    # Текстовая часть (fallback)
    message.set_content(text_body)

    # HTML-часть (основное оформление)
    message.add_alternative(html_body, subtype="html")

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    # При необходимости можно ещё ослабить проверку сертификата:
    # tls_context.verify_mode = ssl.CERT_NONE

    try:
        logger.info("Отправляет письмо с кодом подтверждения на %s", to_email)
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            start_tls=settings.smtp_start_tls,
            tls_context=tls_context,
        )
        logger.info("Письмо с кодом подтверждения успешно отправлено на %s", to_email)
    except Exception as exc:
        logger.exception("Ошибка при отправке письма с кодом подтверждения на %s", to_email)
        raise



async def send_password_reset_code(to_email: str, code: str) -> None:
    """
    Отправляет письмо с кодом для сброса пароля.
    Формирует multipart/alternative: текст + HTML.
    """
    subject = "Pature · Сброс пароля"

    text_body = (
        "Здравствуйте!\n\n"
        "Вы запросили сброс пароля в приложении Pature.\n\n"
        f"Код для сброса пароля:\n\n"
        f"    {code}\n\n"
        "Если вы не запрашивали сброс пароля, просто игнорируйте это письмо.\n\n"
        "С уважением,\n"
        "команда Pature"
    )

    html_body = f"""\
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Сброс пароля</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center" style="padding:24px 16px;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:480px;background-color:#ffffff;border-radius:12px;box-shadow:0 4px 16px rgba(15,23,42,0.08);overflow:hidden;">
                    <tr>
                        <td style="padding:20px 24px 16px 24px;border-bottom:1px solid #eef1f7;">
                            <div style="font-size:18px;font-weight:600;color:#111827;">Pature</div>
                            <div style="margin-top:4px;font-size:14px;color:#6b7280;">Сброс пароля</div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 24px 8px 24px;font-size:14px;color:#111827;line-height:1.6;">
                            <p style="margin:0 0 12px 0;">Здравствуйте!</p>
                            <p style="margin:0 0 12px 0;">
                                Вы запросили сброс пароля в сервисе Pature.
                                Используйте следующий код для подтверждения операции:
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding:8px 24px 16px 24px;">
                            <div style="
                                display:inline-block;
                                padding:12px 24px;
                                border-radius:999px;
                                background:linear-gradient(135deg,#4f46e5,#6366f1);
                                color:#ffffff;
                                font-size:20px;
                                font-weight:700;
                                letter-spacing:0.20em;
                                text-align:center;
                            ">
                                {code}
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:0 24px 16px 24px;font-size:13px;color:#4b5563;line-height:1.6;">
                            <p style="margin:0 0 8px 0;">
                                По соображениям безопасности никому не передавайте этот код и не пересылайте это письмо.
                            </p>
                            <p style="margin:0 0 8px 0;">
                                Если вы не запрашивали сброс пароля, проигнорируйте это письмо или при необходимости свяжитесь с поддержкой.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:8px 24px 20px 24px;font-size:12px;color:#9ca3af;border-top:1px solid #eef1f7;">
                            <p style="margin:8px 0 0 0;">
                                С уважением,<br>
                                команда Pature
                            </p>
                        </td>
                    </tr>
                </table>
                <div style="margin-top:12px;font-size:11px;color:#9ca3af;max-width:480px;">
                    Вы получили это письмо, потому что указали данный адрес электронной почты в приложении Pature.
                </div>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    # При необходимости можно ещё ослабить проверку сертификата:
    # tls_context.verify_mode = ssl.CERT_NONE

    try:
        logger.info("Отправляет письмо с кодом для сброса пароля на %s", to_email)
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            start_tls=settings.smtp_start_tls,
            tls_context=tls_context,
        )
        logger.info("Письмо с кодом для сброса пароля успешно отправлено на %s", to_email)
    except Exception:
        logger.exception("Ошибка при отправке письма с кодом для сброса пароля на %s", to_email)
        raise