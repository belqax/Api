import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_user
from ..models import User, EmailVerificationCode, UserProfile, UserPrivacySettings, UserSettings
from ..schemas import (
    EmailRegisterRequest,
    RegisterStartResponse,
    EmailVerificationConfirmRequest,
    SimpleDetailResponse,
    TokenPair,
    UserLoginRequest,
)
from ..security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_numeric_code,
    hash_verification_code,
    verify_verification_code,
)
from ..repositories.user_repository import (
    get_user_by_phone,
    upsert_device,
    create_session,
    get_session_by_refresh_token,
    revoke_session,
)
from app.services.email_service import send_email_verification_code
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post(
    "/register",
    response_model=RegisterStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def register(
    payload: EmailRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterStartResponse:
    # Проверяет, есть ли пользователь с таким email
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    hashed_pwd = hash_password(payload.password)

    if user and user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already registered",
        )

    if user is None:
        # Создаёт нового пользователя и дефолтные записи профиля/настроек
        user = User(
            email=payload.email,
            phone=payload.phone,
            hashed_password=hashed_pwd,
            is_active=True,
            is_email_verified=False,
        )
        db.add(user)
        await db.flush()  # получит user.id

        db.add(UserProfile(user_id=user.id))
        db.add(UserPrivacySettings(user_id=user.id))
        db.add(UserSettings(user_id=user.id))
    else:
        # Пользователь есть, но ещё не подтвердил почту – обновляет пароль
        user.hashed_password = hashed_pwd

    # Генерирует одноразовый код
    code = generate_numeric_code(6)
    code_hash = hash_verification_code(code)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        minutes=settings.email_verification_code_ttl_minutes
    )

    verification = EmailVerificationCode(
        user_id=user.id,
        email=payload.email,
        purpose="register",
        code_hash=code_hash,
        expires_at=expires_at,
        max_attempts=settings.email_verification_max_attempts,
    )
    db.add(verification)
    await db.commit()

    # Отправляет письмо
    await send_email_verification_code(payload.email, code)
    # try:
    #     await send_email_verification_code(payload.email, code)
    # except Exception:
    #     # Здесь можно добавить логирование
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Could not send verification email",
    #     )

    return RegisterStartResponse()

@router.post(
    "/register/confirm",
    response_model=SimpleDetailResponse,
)
async def confirm_email(
    payload: EmailVerificationConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> SimpleDetailResponse:
    # Находит пользователя по email
    stmt_user = select(User).where(User.email == payload.email)
    result_user = await db.execute(stmt_user)
    user = result_user.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    if user.is_email_verified:
        return SimpleDetailResponse(detail="email_already_verified")

    now = dt.datetime.now(dt.timezone.utc)

    # Берёт последний активный код
    stmt_code = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.email == payload.email,
            EmailVerificationCode.purpose == "register",
            EmailVerificationCode.consumed_at.is_(None),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    result_code = await db.execute(stmt_code)
    code_row = result_code.scalar_one_or_none()

    if code_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code",
        )

    if code_row.attempt_count >= code_row.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded",
        )

    if not verify_verification_code(payload.code, code_row.code_hash):
        code_row.attempt_count += 1
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Код корректен – помечает как использованный и подтверждает e-mail
    code_row.consumed_at = now
    user.is_email_verified = True
    await db.commit()

    return SimpleDetailResponse(detail="email_verified")


@router.post("/login", response_model=TokenPair)
async def login(
    payload: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    user = await get_user_by_phone(db, payload.phone)
    if user is None or not user.is_active or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password",
        )
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not verified",
        )

    device_id_header = request.headers.get("X-Device-Id")
    device_uuid = UUID(device_id_header) if device_id_header else UUID(int=0)
    platform = request.headers.get("X-Platform", "android")
    device_model = request.headers.get("X-Device-Model")
    os_version = request.headers.get("X-OS-Version")
    app_version = request.headers.get("X-App-Version")
    push_token = request.headers.get("X-Push-Token")

    now = dt.datetime.now(dt.timezone.utc)
    ip = request.client.host if request.client else None

    device = await upsert_device(
        db,
        user_id=user.id,
        device_uuid=device_uuid,
        platform=platform,
        device_model=device_model,
        os_version=os_version,
        app_version=app_version,
        push_token=push_token,
        ip=ip,
        now=now,
    )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()
    refresh_expires_at = now + dt.timedelta(days=30)

    await create_session(
        db,
        user_id=user.id,
        device_id=device.id,
        refresh_token_plain=refresh_token,
        refresh_expires_at=refresh_expires_at,
        ip=ip,
        user_agent=request.headers.get("User-Agent"),
    )

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    data = await request.json()
    refresh_token = data.get("refresh_token")
    phone = data.get("phone")
    if not refresh_token or not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone and refresh_token are required",
        )

    user = await get_user_by_phone(db, phone)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    session = await get_session_by_refresh_token(
        db,
        user_id=user.id,
        refresh_token_plain=refresh_token,
    )
    if session is None or not session.is_current or session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    now = dt.datetime.now(dt.timezone.utc)
    if session.refresh_expires_at < now:
        await revoke_session(db, session, reason="expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token()
    new_refresh_expires = now + dt.timedelta(days=30)

    await revoke_session(db, session, reason="rotation")
    await create_session(
        db,
        user_id=user.id,
        device_id=session.device_id,
        refresh_token_plain=new_refresh,
        refresh_expires_at=new_refresh_expires,
        ip=session.ip_address,
        user_agent=session.user_agent,
    )

    return TokenPair(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await request.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )

    session = await get_session_by_refresh_token(
        db,
        user_id=current_user.id,
        refresh_token_plain=refresh_token,
    )
    if session is None:
        return {"detail": "already logged out"}

    await revoke_session(db, session, reason="logout")
    return {"detail": "ok"}
