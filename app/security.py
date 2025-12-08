import datetime as dt
import hashlib
import secrets
from typing import Any, Dict

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    sha = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(sha)


def verify_password(password: str, hashed: str) -> bool:
    sha = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.verify(sha, hashed)

def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    expires = now + dt.timedelta(minutes=15)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return pwd_context.hash(token)


def verify_refresh_token(token: str, hashed: str) -> bool:
    return pwd_context.verify(token, hashed)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def generate_numeric_code(length: int = 6) -> str:
    """
    Генерирует одноразовый числовой код указанной длины.
    """
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_verification_code(code: str) -> str:
    """
    Хеширует код подтверждения.
    """
    return pwd_context.hash(code)


def verify_verification_code(code: str, code_hash: str) -> bool:
    """
    Проверяет код подтверждения по хешу.
    """
    try:
        return pwd_context.verify(code, code_hash)
    except Exception:
        return False