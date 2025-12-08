from fastapi import APIRouter, Depends
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
from ..repositories.user_repository import update_profile

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
    user = await update_profile(
        db,
        current_user,
        display_name=payload.display_name,
        age=payload.age,
        about=payload.about,
        location=payload.location,
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
