from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text, func, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32),unique=True,index=True,nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        lazy="selectin",
        uselist=False,
    )

    privacy_settings: Mapped[Optional["UserPrivacySettings"]] = relationship(
        "UserPrivacySettings",
        back_populates="user",
        lazy="selectin",
        uselist=False,
    )

    settings: Mapped[Optional["UserSettings"]] = relationship(
        "UserSettings",
        back_populates="user",
        lazy="selectin",
        uselist=False,
    )
    devices: Mapped[List["UserDevice"]] = relationship(back_populates="user")
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="user")
    animals: Mapped[List["Animal"]] = relationship(back_populates="owner")
    email_verification_codes: Mapped[list["EmailVerificationCode"]] = relationship(
        "EmailVerificationCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    animals: Mapped[List["Animal"]] = relationship(back_populates="owner")
    email_verification_codes: Mapped[list["EmailVerificationCode"]] = relationship(
        "EmailVerificationCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    sent_likes: Mapped[list["AnimalLike"]] = relationship(
        "AnimalLike",
        back_populates="from_user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    matches_as_user1: Mapped[list["UserMatch"]] = relationship(
        "UserMatch",
        back_populates="user1",
        foreign_keys="UserMatch.user_id1",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    matches_as_user2: Mapped[list["UserMatch"]] = relationship(
        "UserMatch",
        back_populates="user2",
        foreign_keys="UserMatch.user_id2",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    search_history: Mapped[list["UserSearchHistory"]] = relationship(
        "UserSearchHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    age: Mapped[Optional[int]] = mapped_column(Integer)
    about: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile")


class UserPrivacySettings(Base):
    __tablename__ = "user_privacy_settings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    profile_visibility: Mapped[str] = mapped_column(String(32), default="everyone", nullable=False)
    photos_visibility: Mapped[str] = mapped_column(String(32), default="matches", nullable=False)
    online_status_visibility: Mapped[str] = mapped_column(
        String(32), default="contacts", nullable=False
    )
    last_seen_precision: Mapped[str] = mapped_column(
        String(32), default="minutes", nullable=False
    )

    show_age: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_distance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="privacy_settings")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    language_code: Mapped[str] = mapped_column(String(16), default="ru", nullable=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(64))

    biometric_login_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_new_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_events: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_news: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="settings")


class UserDevice(Base):
    __tablename__ = "user_devices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    device_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    device_model: Mapped[Optional[str]] = mapped_column(String(128))
    os_version: Mapped[Optional[str]] = mapped_column(String(64))
    app_version: Mapped[Optional[str]] = mapped_column(String(32))

    push_token: Mapped[Optional[str]] = mapped_column(String(512))
    is_push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_ip: Mapped[Optional[str]] = mapped_column(INET)
    last_seen_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="devices")
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="device")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("user_devices.id", ondelete="SET NULL")
    )

    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))

    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(255))

    last_access_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")
    device: Mapped[Optional[UserDevice]] = relationship(back_populates="sessions")

class UserSearchHistory(Base):
    __tablename__ = "user_search_history"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # источник: animals_search, feed и т.п.
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    # JSON с фильтрами: species, city, age_from_years и т.д.
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="search_history")


class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[Optional[str]] = mapped_column(String(100))
    species: Mapped[str] = mapped_column(String(32), nullable=False)
    breed: Mapped[Optional[str]] = mapped_column(String(64))

    sex: Mapped[Optional[str]] = mapped_column(String(16))
    date_of_birth: Mapped[Optional[dt.date]] = mapped_column(Date)
    approx_age_years: Mapped[Optional[int]] = mapped_column(Integer)
    approx_age_months: Mapped[Optional[int]] = mapped_column(Integer)

    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    height_cm: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    color: Mapped[Optional[str]] = mapped_column(String(64))
    pattern: Mapped[Optional[str]] = mapped_column(String(64))

    is_neutered: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_vaccinated: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_chipped: Mapped[Optional[bool]] = mapped_column(Boolean)
    chip_number: Mapped[Optional[str]] = mapped_column(String(64))

    temperament_note: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    city: Mapped[Optional[str]] = mapped_column(String(128))
    geo_lat: Mapped[Optional[float]] = mapped_column(Numeric(9, 6))
    geo_lng: Mapped[Optional[float]] = mapped_column(Numeric(9, 6))

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="animals")
    photos: Mapped[list["AnimalPhoto"]] = relationship(
        back_populates="animal",
        cascade="all, delete",
        lazy="selectin",
    )
    owner: Mapped[User] = relationship(back_populates="animals")
    photos: Mapped[list["AnimalPhoto"]] = relationship(
        back_populates="animal",
        cascade="all, delete",
        lazy="selectin",
    )

    received_likes: Mapped[list["AnimalLike"]] = relationship(
        "AnimalLike",
        back_populates="animal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AnimalPhoto(Base):
    __tablename__ = "animal_photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    animal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False
    )

    url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumb_url: Mapped[Optional[str]] = mapped_column(String(500))  # <-- новое поле
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    animal: Mapped[Animal] = relationship(back_populates="photos")


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="register")
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    consumed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="email_verification_codes")

class AnimalLike(Base):
    __tablename__ = "animal_likes"
    __table_args__ = (
        UniqueConstraint(
            "from_user_id",
            "animal_id",
            name="uq_animal_likes_from_user_animal",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    from_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    animal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("animals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "like" или "dislike"
    result: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    from_user: Mapped["User"] = relationship(
        "User",
        back_populates="sent_likes",
    )
    animal: Mapped["Animal"] = relationship(
        "Animal",
        back_populates="received_likes",
    )


class UserMatch(Base):
    __tablename__ = "user_matches"
    __table_args__ = (
        UniqueConstraint(
            "user_id1",
            "user_id2",
            name="uq_user_matches_pair",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # Инвариант: user_id1 < user_id2
    user_id1: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id2: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    # В перспективе можно добавить поля архивации/блокировки
    # is_active, archived_by_user1, archived_by_user2 и т.п.

    user1: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id1],
        back_populates="matches_as_user1",
    )
    user2: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id2],
        back_populates="matches_as_user2",
    )