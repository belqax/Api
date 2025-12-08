import datetime as dt
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    User,
    UserProfile,
    UserPrivacySettings,
    UserSettings,
    UserDevice,
    UserSession,
)
from ..security import hash_refresh_token


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


async def update_profile(
    db: AsyncSession,
    user: User,
    *,
    display_name: Optional[str],
    age: Optional[int],
    about: Optional[str],
    location: Optional[str],
) -> User:
    if user.profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
        await db.refresh(user)
    profile = user.profile
    if display_name is not None:
        profile.display_name = display_name
    if age is not None:
        profile.age = age
    if about is not None:
        profile.about = about
    if location is not None:
        profile.location = location
    await db.commit()
    await db.refresh(user)
    return user
