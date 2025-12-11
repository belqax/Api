import datetime as dt
import logging
from typing import Optional, Any, Coroutine
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User
from ..models import (
    User,
    UserProfile,
    UserPrivacySettings,
    UserSettings,
    UserDevice,
    UserSession,
)
from ..security import hash_refresh_token

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user_with_defaults(
    db: AsyncSession,
    *,
    phone: str,
    password_hash: Optional[str],
    email: Optional[str] = None,
) -> User:
    user = User(
        phone=phone,
        email=email,
        hashed_password=password_hash,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    profile = UserProfile(user_id=user.id)
    privacy = UserPrivacySettings(user_id=user.id)
    settings = UserSettings(user_id=user.id)
    db.add_all([profile, privacy, settings])

    await db.commit()
    await db.refresh(user)
    return user


async def upsert_device(
    db: AsyncSession,
    *,
    user_id: int,
    device_uuid: UUID,
    platform: str,
    device_model: Optional[str],
    os_version: Optional[str],
    app_version: Optional[str],
    push_token: Optional[str],
    ip: Optional[str],
    now: dt.datetime,
) -> UserDevice:
    stmt = select(UserDevice).where(
        UserDevice.user_id == user_id,
        UserDevice.device_id == str(device_uuid),
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        device = UserDevice(
            user_id=user_id,
            device_id=str(device_uuid),
            platform=platform,
            device_model=device_model,
            os_version=os_version,
            app_version=app_version,
            push_token=push_token,
            last_ip=ip,
            last_seen_at=now,
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device

    device.platform = platform
    device.device_model = device_model
    device.os_version = os_version
    device.app_version = app_version
    device.push_token = push_token
    device.last_ip = ip
    device.last_seen_at = now
    await db.commit()
    await db.refresh(device)
    return device

async def create_session(
    db: AsyncSession,
    *,
    user_id: int,
    device_id: Optional[int],
    refresh_token_plain: str,
    refresh_expires_at: dt.datetime,
    ip: Optional[str],
    user_agent: Optional[str],
) -> UserSession:
    refresh_hash = hash_refresh_token(refresh_token_plain)
    session = UserSession(
        user_id=user_id,
        device_id=device_id,
        refresh_token_hash=refresh_hash,
        refresh_expires_at=refresh_expires_at,
        ip_address=ip,
        user_agent=user_agent,
        is_current=True,
        last_access_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_refresh_token(
    db: AsyncSession,
    *,
    user_id: int,
    refresh_token_plain: str,
) -> Optional[UserSession]:
    # сначала достаём все активные сессии и фильтруем по verify
    stmt = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.is_current.is_(True),
        UserSession.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    from ..security import verify_refresh_token

    for s in sessions:
        if verify_refresh_token(refresh_token_plain, s.refresh_token_hash):
            return s
    return None


async def revoke_session(
    db: AsyncSession,
    session: UserSession,
    *,
    reason: str,
) -> None:
    session.is_current = False
    session.revoked_at = dt.datetime.now(dt.timezone.utc)
    session.revoke_reason = reason
    await db.commit()

async def _load_user_with_profile(
    db: AsyncSession,
    user_id: int,
) -> User:
    """
    Загружает пользователя с profile / privacy_settings / settings
    в контексте текущей сессии.
    """
    stmt = (
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.privacy_settings),
            selectinload(User.settings),
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise ValueError(f"User with id={user_id} not found or inactive")

    return user


async def _ensure_profile(
    db: AsyncSession,
    user: User,
) -> UserProfile:
    """
    Гарантирует наличие user.profile.
    При отсутствии создаёт новый профиль и привязывает к пользователю.
    """
    if user.profile is not None:
        return user.profile

    logger.info("Creating profile for user_id=%s", user.id)
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    # Фиксирует появление профиля и обновляет user.profile
    await db.flush()
    await db.refresh(user, attribute_names=["profile"])

    return user.profile  # type: ignore[return-value]


async def load_user_with_all_relations(
    db: AsyncSession,
    user_id: int,
) -> User:
    """
    Загружает пользователя с profile / privacy_settings / settings в текущей сессии.
    """
    stmt = (
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.privacy_settings),
            selectinload(User.settings),
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise ValueError(f"User with id={user_id} not found or inactive")

    return user


# ===================== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ =====================


async def update_profile(
    db: AsyncSession,
    user_id: int,
    *,
    display_name: Optional[str] = None,
    age: Optional[int] = None,
    about: Optional[str] = None,
    location: Optional[str] = None,
) -> User:
    """
    Обновляет профиль пользователя по user_id.

    ЛОГИКА:
    - Собирает словарь полей, которые реально переданы (partial update).
    - Если профиля нет → делает INSERT.
    - Если профиль есть → делает явный UPDATE по user_id.
    - После коммита перегружает пользователя с привязанными сущностями.
    """
    payload: dict[str, Any] = {
        "display_name": display_name,
        "age": age,
        "about": about,
        "location": location,
    }
    # Оставляет только реально переданные значения (не None)
    update_fields = {k: v for k, v in payload.items() if v is not None}

    logger.info(
        "update_profile(): user_id=%s raw=%s update_fields=%s",
        user_id,
        payload,
        update_fields,
    )

    # Если нечего обновлять, просто возвращает актуального пользователя
    if not update_fields:
        user = await load_user_with_all_relations(db, user_id=user_id)
        return user

    # Проверяет, существует ли профиль
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    now = dt.datetime.now(dt.timezone.utc)

    if profile is None:
        # Вставляет новый профиль
        logger.info("update_profile(): creating new profile for user_id=%s", user_id)

        new_profile = UserProfile(
            user_id=user_id,
            **update_fields,
            created_at=now,
            updated_at=now,
        )
        db.add(new_profile)
    else:
        # Делает явный UPDATE (без зависимости от ORM-статуса инстанса)
        logger.info("update_profile(): updating existing profile for user_id=%s", user_id)

        update_fields["updated_at"] = now

        await db.execute(
            update(UserProfile)
            .where(UserProfile.user_id == user_id)
            .values(**update_fields)
        )

    await db.commit()

    # Перегружает пользователя целиком
    user = await load_user_with_all_relations(db, user_id=user_id)

    logger.info(
        "update_profile(): saved for user_id=%s => profile=%s",
        user_id,
        {
            "display_name": user.profile.display_name if user.profile else None,
            "age": user.profile.age if user.profile else None,
            "about": user.profile.about if user.profile else None,
            "location": user.profile.location if user.profile else None,
        },
    )

    return user


# ===================== АВАТАР ПОЛЬЗОВАТЕЛЯ =====================


async def update_user_avatar(
    db: AsyncSession,
    *,
    user_id: int,
    avatar_url: Optional[str],
) -> User:
    """
    Обновляет avatar_url в профиле пользователя.
    Если профиля нет, создаёт его.
    """
    logger.info(
        "update_user_avatar(): user_id=%s avatar_url=%s",
        user_id,
        avatar_url,
    )

    # Проверяет, существует ли профиль
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    now = dt.datetime.now(dt.timezone.utc)

    if profile is None:
        logger.info(
            "update_user_avatar(): creating new profile for user_id=%s", user_id
        )
        new_profile = UserProfile(
            user_id=user_id,
            avatar_url=avatar_url,
            created_at=now,
            updated_at=now,
        )
        db.add(new_profile)
    else:
        await db.execute(
            update(UserProfile)
            .where(UserProfile.user_id == user_id)
            .values(
                avatar_url=avatar_url,
                updated_at=now,
            )
        )

    await db.commit()

    user = await load_user_with_all_relations(db, user_id=user_id)

    logger.info(
        "update_user_avatar(): saved for user_id=%s => avatar_url=%s",
        user_id,
        user.profile.avatar_url if user.profile else None,
    )

    return user

async def revoke_all_sessions_for_user(
    db: AsyncSession,
    *,
    user_id: int,
    except_session_id: Optional[int] = None,
    reason: str = "bulk_revoke",
) -> None:
    """
    Ревокирует все текущие сессии пользователя.
    Если задан except_session_id, оставляет одну сессию как текущую.
    """
    stmt = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.is_current.is_(True),
        UserSession.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    now = dt.datetime.now(dt.timezone.utc)

    for s in sessions:
        if except_session_id is not None and s.id == except_session_id:
            continue
        s.is_current = False
        s.revoked_at = now
        s.revoke_reason = reason

    await db.commit()
