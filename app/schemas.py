from __future__ import annotations

import datetime as dt
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, EmailStr, constr


# ---------- TOKENS ----------

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ---------- USER / PROFILE ----------

class UserBase(BaseModel):
    id: int
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    display_name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    about: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserPrivacySettings(BaseModel):
    profile_visibility: str = "everyone"
    photos_visibility: str = "matches"
    online_status_visibility: str = "contacts"
    last_seen_precision: str = "minutes"
    show_age: bool = True
    show_distance: bool = True

    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    language_code: str = "ru"
    timezone: Optional[str] = None
    biometric_login_enabled: bool = False
    push_enabled: bool = True
    push_new_messages: bool = True
    push_events: bool = True
    push_news: bool = True

    class Config:
        from_attributes = True


class UserFullProfile(BaseModel):
    user: UserBase
    profile: UserProfile
    privacy: UserPrivacySettings
    settings: UserSettings


class UserRegisterRequest(BaseModel):
    phone: str
    password: Optional[str] = None
    email: Optional[str] = None


class UserLoginRequest(BaseModel):
    login: constr(min_length=3, max_length=255)
    password: constr(min_length=8, max_length=128)

class UserRefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class UserProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    about: Optional[str] = None
    location: Optional[str] = None


class ResendVerificationEmailRequest(BaseModel):
    email: EmailStr


# ---------- ANIMALS ----------

class AnimalPhoto(BaseModel):
    id: int
    url: str
    thumb_url: Optional[str] = None
    is_primary: bool
    position: int

    class Config:
        from_attributes = True


class AnimalBase(BaseModel):
    id: int
    owner_user_id: int
    name: Optional[str] = None
    species: str
    breed: Optional[str] = None
    sex: Optional[str] = None
    date_of_birth: Optional[dt.date] = None
    approx_age_years: Optional[int] = Field(default=None, ge=0, le=50)
    approx_age_months: Optional[int] = Field(default=None, ge=0, le=11)
    weight_kg: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    height_cm: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    color: Optional[str] = None
    pattern: Optional[str] = None
    is_neutered: Optional[bool] = None
    is_vaccinated: Optional[bool] = None
    is_chipped: Optional[bool] = None
    chip_number: Optional[str] = None
    temperament_note: Optional[str] = None
    description: Optional[str] = None
    status: str
    city: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None

    class Config:
        from_attributes = True


class AnimalCreateRequest(BaseModel):
    name: Optional[str] = None
    species: str
    breed: Optional[str] = None
    sex: Optional[str] = None
    date_of_birth: Optional[dt.date] = None
    approx_age_years: Optional[int] = Field(default=None, ge=0, le=50)
    approx_age_months: Optional[int] = Field(default=None, ge=0, le=11)
    weight_kg: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    height_cm: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    color: Optional[str] = None
    pattern: Optional[str] = None
    is_neutered: Optional[bool] = None
    is_vaccinated: Optional[bool] = None
    is_chipped: Optional[bool] = None
    chip_number: Optional[str] = None
    temperament_note: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    city: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None


class AnimalUpdateRequest(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    date_of_birth: Optional[dt.date] = None
    approx_age_years: Optional[int] = Field(default=None, ge=0, le=50)
    approx_age_months: Optional[int] = Field(default=None, ge=0, le=11)
    weight_kg: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    height_cm: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    color: Optional[str] = None
    pattern: Optional[str] = None
    is_neutered: Optional[bool] = None
    is_vaccinated: Optional[bool] = None
    is_chipped: Optional[bool] = None
    chip_number: Optional[str] = None
    temperament_note: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    city: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None


class AnimalWithPhotos(AnimalBase):
    photos: List[AnimalPhoto] = []


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    phone: constr(min_length=5, max_length=32) | None = None


class RegisterStartResponse(BaseModel):
    detail: str = "verification_code_sent"


class EmailVerificationConfirmRequest(BaseModel):
    email: EmailStr
    code: constr(min_length=4, max_length=10)


class SimpleDetailResponse(BaseModel):
    detail: str

class PasswordForgotRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr
    code: constr(min_length=4, max_length=10)
    new_password: constr(min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    old_password: constr(min_length=8, max_length=128)
    new_password: constr(min_length=8, max_length=128)


class SessionsRevokeAllRequest(BaseModel):
    # Если передан refresh_token текущей сессии – её можно оставить,
    # а все остальные сессии ревокнуть. Если None – ревокнуть все.
    refresh_token: constr(min_length=10, max_length=1024) | None = None

# ---------- ANIMAL PHOTOS MANAGEMENT ----------

class AnimalPhotosReorderRequest(BaseModel):
    photo_ids: List[int]

class AnimalStatusUpdateRequest(BaseModel):
    status: Literal["active", "hidden", "adopted", "archived"]