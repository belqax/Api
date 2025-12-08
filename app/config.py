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
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Параметры e-mail подтверждения
    email_verification_code_ttl_minutes: int = 15
    email_verification_max_attempts: int = 5

    # SMTP для отправки писем
    smtp_host: str = "176.109.108.150"
    smtp_port: int = 587
    smtp_user: str = "noreply"
    smtp_password: str = "noreply"
    smtp_use_tls: bool = False          # True для SMTPS (465)
    smtp_start_tls: bool | None = None  # True/False/None (по умолчанию авто)
    smtp_from_email: str = "noreply@belqax.xyz"
    smtp_from_name: str = "Pature"

    # Медиа
    media_root: str = str(PROJECT_ROOT  / "media")
    avatar_subdir: str = "avatars"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT  / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
