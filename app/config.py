from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
# корень проекта (на уровень выше app/)
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    # Общее
    app_name: str = "Pature APIs"
    debug: bool = False

    # База данных
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10
    refresh_token_expire_days: int = 30

    # Верификация e-mail
    email_verification_code_ttl_minutes: int = 15
    email_verification_max_attempts: int = 5

    # Rate-limit на повторную отправку e-mail кода
    email_verification_resend_cooldown_seconds: int = 60
    email_verification_resend_max_per_hour: int = 5

    # Верификация телефона (SMS)
    phone_verification_code_ttl_minutes: int = 15
    phone_verification_max_attempts: int = 5

    # Rate-limit на повторную отправку SMS кода
    phone_verification_resend_cooldown_seconds: int = 60
    phone_verification_resend_max_per_hour: int = 5

    # Сброс пароля (можно использовать те же значения TTL и попыток)
    password_reset_code_ttl_minutes: int = 15
    password_reset_max_attempts: int = 5

    ip_rate_limit_requests_per_minute: int = 60
    ip_rate_limit_block_ttl_seconds: int = 600  # сколько держать блокировку IP
    ip_rate_limit_redis_dsn: str = "redis://localhost:6379/0"

    # SMTP для отправки писем
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 587
    smtp_user: str = "noreply"
    smtp_password: str = "noreply"
    smtp_use_tls: bool = False          # True для SMTPS (465)
    smtp_start_tls: bool | None = True  # True/False/None (по умолчанию авто)
    smtp_from_email: str = "noreply@belqax.xyz"
    smtp_from_name: str = "Pature"

    # Медиа
    media_root: str = str(PROJECT_ROOT / "media")
    avatar_subdir: str = "avatars"
    animal_photos_subdir: str = "animals"  # подкаталог для фото животных

    # Geoapify геокодинг
    geoapify_api_key: str | None = None
    geoapify_base_url: str = "https://api.geoapify.com/v1/geocode/autocomplete"
    geoapify_reverse_url: str = "https://api.geoapify.com/v1/geocode/reverse"
    geoapify_search_url: str = "https://api.geoapify.com/v1/geocode/search"
    geoapify_default_lang: str = "ru"
    geoapify_default_limit: int = 5

    # Параметры изображений животных
    animal_photo_max_bytes: int = 5 * 1024 * 1024          # 5 МБ
    animal_photo_allowed_mime_types: tuple[str, ...] = (
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    )
    animal_photo_max_width: int = 1920
    animal_photo_max_height: int = 1920
    animal_photo_quality: int = 85                         # JPEG/WebP качество

    animal_thumb_max_width: int = 400
    animal_thumb_max_height: int = 400
    animal_thumb_quality: int = 80


    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT  / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
