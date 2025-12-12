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
    UserSettings, UserPrivacyUpdateRequest, UserSettingsUpdateRequest,
)
from ..repositories.user_repository import (
    update_profile,
    update_user_avatar, update_user_privacy_settings, update_user_settings,
)
from ..services.media import delete_media_file_by_url, save_user_avatar_file

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def build_full_profile_response(user: User) -> UserFullProfile:
    """
    Собирает UserFullProfile из ORM-модели User.
    """
    base = UserBase.model_validate(user)

    profile = (
        UserProfile.model_validate(user.profile)
        if user.profile is not None
        else UserProfile()
    )

    privacy = (
        UserPrivacySettings.model_validate(user.privacy_settings)
        if user.privacy_settings is not None
        else UserPrivacySettings()
    )

    settings = (
        UserSettings.model_validate(user.settings)
        if user.settings is not None
        else UserSettings()
    )

    return UserFullProfile(
        user=base,
        profile=profile,
        privacy=privacy,
        settings=settings,
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
    Возвращает профиль текущего пользователя.
    """
    return build_full_profile_response(current_user)


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
    """
    update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)

    try:
        user = await update_profile(
            db,
            user_id=current_user.id,
            **update_data,
        )
    except ValueError as e:
        logger.warning(
            "update_my_profile(): user not found or inactive: %s",
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    return build_full_profile_response(user)


@router.patch(
    "/me/privacy",
    response_model=UserFullProfile,
    status_code=status.HTTP_200_OK,
)
async def update_my_privacy_settings(
    payload: UserPrivacyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    """
    Частично обновляет настройки приватности текущего пользователя.
    """
    update_data = payload.model_dump(exclude_unset=True)

    user = await update_user_privacy_settings(
        db,
        user_id=current_user.id,
        updates=update_data,
    )

    return build_full_profile_response(user)



@router.patch(
    "/me/settings",
    response_model=UserFullProfile,
    status_code=status.HTTP_200_OK,
)
async def update_my_settings(
    payload: UserSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    """
    Частично обновляет settings текущего пользователя.
    """
    update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)

    user = await update_user_settings(
        db,
        user_id=current_user.id,
        updates=update_data,
    )

    return build_full_profile_response(user)

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
    Загружает новый аватар, обновляет profile.avatar_url и удаляет старый файл.
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

    try:
        new_avatar_url = await save_user_avatar_file(
            owner_user_id=current_user.id,
            file=file,
        )
    except Exception as e:
        logger.exception("upload_avatar(): failed to save avatar: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить аватар",
        ) from e

    try:
        user = await update_user_avatar(
            db,
            user_id=current_user.id,
            avatar_url=new_avatar_url,
        )
    except ValueError as e:
        logger.warning(
            "upload_avatar(): user not found or inactive: %s", e
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    if old_avatar_url and old_avatar_url != new_avatar_url:
        try:
            await delete_media_file_by_url(old_avatar_url)
        except Exception as e:
            logger.warning(
                "upload_avatar(): failed to delete old avatar '%s': %s",
                old_avatar_url,
                e,
            )

    return build_full_profile_response(user)


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
    Очищает avatar_url и удаляет файл аватара, если он был.
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
            "delete_avatar(): user not found or inactive: %s", e
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
                "delete_avatar(): failed to delete old avatar '%s': %s",
                old_avatar_url,
                e,
            )

    return build_full_profile_response(user)
