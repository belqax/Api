from __future__ import annotations

import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import (
    UserBase,
    UserFullProfile,
    UserPrivacySettings,
    UserProfile,
    UserProfileUpdateRequest,
    UserSettings,
)
from ..repositories.user_repository import (
    update_profile,
    update_user_avatar,
)
from ..services.media import (
    delete_media_file_by_url,
    save_user_avatar_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def _build_full_profile_response(user: User) -> UserFullProfile:
    """
    Собирает UserFullProfile из ORM-модели User.
    Гарантирует, что профиль/настройки всегда есть в ответе.
    """
    base = UserBase.model_validate(user)

    profile_model = (
        UserProfile.model_validate(user.profile)
        if user.profile is not None
        else UserProfile()
    )

    privacy_model = (
        UserPrivacySettings.model_validate(user.privacy_settings)
        if user.privacy_settings is not None
        else UserPrivacySettings()
    )

    settings_model = (
        UserSettings.model_validate(user.settings)
        if user.settings is not None
        else UserSettings()
    )

    return UserFullProfile(
        user=base,
        profile=profile_model,
        privacy=privacy_model,
        settings=settings_model,
    )


@router.get(
    "/me",
    response_model=UserFullProfile,
    status_code=status.HTTP_200_OK,
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    """
    Возвращает текущий профиль пользователя.
    """
    return _build_full_profile_response(current_user)


@router.put(
    "/me/profile",
    response_model=UserFullProfile,
    status_code=status.HTTP_200_OK,
)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    """
    Частично обновляет профиль текущего пользователя.

    Обновляет только поля, которые реально переданы (exclude_unset=True).
    """
    update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)

    logger.info(
        "UPDATE PROFILE REQUEST: user_id=%s raw=%s fields=%s",
        current_user.id,
        payload.model_dump(),
        update_data,
    )

    if not update_data:
        # Нечего обновлять: просто вернёт текущий профиль
        return _build_full_profile_response(current_user)

    try:
        user = await update_profile(
            db,
            user_id=current_user.id,
            **update_data,
        )
    except ValueError as e:
        logger.warning(
            "update_my_profile: user not found or inactive: %s", e
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    return _build_full_profile_response(user)


@router.post(
    "/me/avatar",
    response_model=UserFullProfile,
    status_code=status.HTTP_200_OK,
)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    """
    Заменяет аватар пользователя на новый файл.
    Старый файл удаляет из хранилища, если он был.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется файл изображения",
        )

    old_avatar_url = (
        current_user.profile.avatar_url
        if current_user.profile is not None
        else None
    )

    # Сохраняет новый файл в хранилище и получает URL
    try:
        new_avatar_url = await save_user_avatar_file(
            user_id=current_user.id,
            file=file,
        )
    except Exception as e:
        logger.exception("Failed to save avatar file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить аватар",
        ) from e

    # Обновляет профиль в базе
    try:
        user = await update_user_avatar(
            db,
            user_id=current_user.id,
            avatar_url=new_avatar_url,
        )
    except ValueError as e:
        logger.warning(
            "upload_avatar: user not found or inactive: %s", e
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    # Пытается удалить старый файл (ошибки не считаются критичными)
    if old_avatar_url and old_avatar_url != new_avatar_url:
        try:
            await delete_media_file_by_url(old_avatar_url)
        except Exception as e:
            logger.warning(
                "Failed to delete old avatar file '%s': %s",
                old_avatar_url,
                e,
            )

    return _build_full_profile_response(user)


@router.delete(
    "/me/avatar",
    response_model=UserFullProfile,
    status_code=status.HTTP_200_OK,
)
async def delete_avatar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    """
    Удаляет аватар пользователя и очищает avatar_url в профиле.
    """
    old_avatar_url = (
        current_user.profile.avatar_url
        if current_user.profile is not None
        else None
    )

    try:
        user = await update_user_avatar(
            db,
            user_id=current_user.id,
            avatar_url=None,
        )
    except ValueError as e:
        logger.warning(
            "delete_avatar: user not found or inactive: %s", e
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    if old_avatar_url:
        try:
            await delete_media_file_by_url(old_avatar_url)
        except Exception as e:
            logger.warning(
                "Failed to delete old avatar file '%s': %s",
                old_avatar_url,
                e,
            )

    return _build_full_profile_response(user)
