from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas import (
    UserBase,
    UserProfile,
    UserPrivacySettings,
    UserSettings,
    UserFullProfile,
    UserProfileUpdateRequest,
)
from ..repositories.user_repository import update_profile, update_user_avatar
from ..services.media import delete_media_file_by_url, save_user_avatar_file

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=UserFullProfile)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    base = UserBase.model_validate(current_user)
    profile = UserProfile.model_validate(current_user.profile)
    privacy = UserPrivacySettings.model_validate(current_user.privacy_settings)
    settings = UserSettings.model_validate(current_user.settings)

    return UserFullProfile(
        user=base,
        profile=profile,
        privacy=privacy,
        settings=settings,
    )


@router.put("/profile", response_model=UserFullProfile)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserFullProfile:
    print("=== UPDATE PROFILE REQUEST ===")
    print("RAW PAYLOAD:", payload.model_dump())
    update_data = payload.model_dump(exclude_unset=True)
    print("FIELDS TO UPDATE (exclude_unset=True):", update_data)
    print("================================")

    user = await update_profile(
        db,
        current_user,
        **update_data,
    )

    print("=== PROFILE AFTER update_profile ===")
    print("PROFILE NOW:", {
        "display_name": user.profile.display_name,
        "age": user.profile.age,
        "about": user.profile.about,
        "location": user.profile.location,
    })
    print("====================================")

    base = UserBase.model_validate(user)
    profile = UserProfile.model_validate(user.profile)
    privacy = UserPrivacySettings.model_validate(user.privacy_settings)
    settings = UserSettings.model_validate(user.settings)

    return UserFullProfile(
        user=base, profile=profile, privacy=privacy, settings=settings
    )

@router.post(
    "/avatar",
    response_model=UserFullProfile,
    summary="Upload or replace my avatar",
)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserFullProfile:
    # Сохраняет новый файл
    new_url = await save_user_avatar_file(
        owner_user_id=current_user.id,
        file=file,
    )

    # Если была старая аватарка — удаляет
    old_url = current_user.profile.avatar_url if current_user.profile else None
    if old_url:
        delete_media_file_by_url(old_url)

    user = await update_user_avatar(
        db,
        user=current_user,
        avatar_url=new_url,
    )

    base = UserBase.model_validate(user)
    profile = UserProfile.model_validate(user.profile)
    privacy = UserPrivacySettings.model_validate(user.privacy_settings)
    settings = UserSettings.model_validate(user.settings)

    return UserFullProfile(
        user=base,
        profile=profile,
        privacy=privacy,
        settings=settings,
    )


@router.delete(
    "/avatar",
    response_model=UserFullProfile,
    summary="Delete my avatar",
)
async def delete_my_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserFullProfile:
    old_url = current_user.profile.avatar_url if current_user.profile else None
    if not old_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar is not set",
        )

    delete_media_file_by_url(old_url)

    user = await update_user_avatar(
        db,
        user=current_user,
        avatar_url=None,
    )

    base = UserBase.model_validate(user)
    profile = UserProfile.model_validate(user.profile)
    privacy = UserPrivacySettings.model_validate(user.privacy_settings)
    settings = UserSettings.model_validate(user.settings)

    return UserFullProfile(
        user=base,
        profile=profile,
        privacy=privacy,
        settings=settings,
    )