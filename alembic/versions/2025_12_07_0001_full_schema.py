from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2025_12_07_0001_full_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),

        sa.Column("phone", sa.String(length=32), nullable=True, unique=True),

        sa.Column("email", sa.String(length=255), nullable=True, unique=True),

        sa.Column("is_phone_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),

        sa.Column("hashed_password", sa.String(length=255), nullable=True),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)

    # user_profiles
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),

        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),

        # avatar
        sa.Column("avatar_url", sa.String(length=500), nullable=True),

        # structured location fields (2025_12_12_add_profile_location_fields)
        sa.Column("location_formatted", sa.String(length=256), nullable=True),
        sa.Column("location_city", sa.String(length=128), nullable=True),
        sa.Column("location_state", sa.String(length=128), nullable=True),
        sa.Column("location_country", sa.String(length=128), nullable=True),
        sa.Column("location_postcode", sa.String(length=32), nullable=True),
        sa.Column("location_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("location_lon", sa.Numeric(9, 6), nullable=True),
        sa.Column("location_result_type", sa.String(length=64), nullable=True),
        sa.Column("location_confidence", sa.Numeric(4, 3), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_user_profiles_location_city", "user_profiles", ["location_city"], unique=False)
    op.create_index("ix_user_profiles_location_lat_lon", "user_profiles", ["location_lat", "location_lon"], unique=False)

    # user_privacy_settings
    op.create_table(
        "user_privacy_settings",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("profile_visibility", sa.String(length=32), nullable=False, server_default="everyone"),
        sa.Column("photos_visibility", sa.String(length=32), nullable=False, server_default="matches"),
        sa.Column("online_status_visibility", sa.String(length=32), nullable=False, server_default="contacts"),
        sa.Column("last_seen_precision", sa.String(length=32), nullable=False, server_default="minutes"),
        sa.Column("show_age", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("show_distance", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # user_settings
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("language_code", sa.String(length=16), nullable=False, server_default="ru"),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("biometric_login_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_new_messages", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_events", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_news", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # user_devices
    op.create_table(
        "user_devices",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("device_model", sa.String(length=128), nullable=True),
        sa.Column("os_version", sa.String(length=64), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("push_token", sa.String(length=512), nullable=True),
        sa.Column("is_push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_ip", postgresql.INET(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "device_id", name="uq_user_devices_user_device"),
    )
    op.create_index("idx_user_devices_user_id", "user_devices", ["user_id"], unique=False)

    # user_sessions (исправлено на BigInteger)
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("user_devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=255), nullable=True),
        sa.Column("last_access_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("idx_user_sessions_refresh_hash", "user_sessions", ["refresh_token_hash"], unique=False)

    # animals
    op.create_table(
        "animals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("owner_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),

        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("species", sa.String(length=32), nullable=False),
        sa.Column("breed", sa.String(length=64), nullable=True),

        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("approx_age_years", sa.Integer(), nullable=True),
        sa.Column("approx_age_months", sa.Integer(), nullable=True),

        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("height_cm", sa.Numeric(5, 2), nullable=True),

        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("pattern", sa.String(length=64), nullable=True),

        sa.Column("is_neutered", sa.Boolean(), nullable=True),
        sa.Column("is_vaccinated", sa.Boolean(), nullable=True),
        sa.Column("is_chipped", sa.Boolean(), nullable=True),
        sa.Column("chip_number", sa.String(length=64), nullable=True),

        sa.Column("temperament_note", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),

        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),

        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("geo_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("geo_lng", sa.Numeric(9, 6), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_animals_owner", "animals", ["owner_user_id"], unique=False)
    op.create_index("idx_animals_status", "animals", ["status"], unique=False)
    op.create_index("idx_animals_species", "animals", ["species"], unique=False)

    # animal_photos (+ thumb_url)
    op.create_table(
        "animal_photos",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("animal_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("thumb_url", sa.String(length=500), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_animal_photos_animal_id", "animal_photos", ["animal_id"], unique=False)

    # email_verification_codes
    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="register"),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_email_verification_codes_email_purpose",
        "email_verification_codes",
        ["email", "purpose"],
        unique=False,
    )

    # animal_likes
    op.create_table(
        "animal_likes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("from_user_id", sa.BigInteger(), nullable=False),
        sa.Column("animal_id", sa.BigInteger(), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("from_user_id", "animal_id", name="uq_animal_likes_from_user_animal"),
    )
    op.create_index("ix_animal_likes_from_user_id", "animal_likes", ["from_user_id"], unique=False)
    op.create_index("ix_animal_likes_animal_id", "animal_likes", ["animal_id"], unique=False)

    # user_matches
    op.create_table(
        "user_matches",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id1", sa.BigInteger(), nullable=False),
        sa.Column("user_id2", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id1"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id2"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id1", "user_id2", name="uq_user_matches_pair"),
    )
    op.create_index("ix_user_matches_user_id1", "user_matches", ["user_id1"], unique=False)
    op.create_index("ix_user_matches_user_id2", "user_matches", ["user_id2"], unique=False)

    # user_search_history
    op.create_table(
        "user_search_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_search_history_user_id", "user_search_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_search_history_user_id", table_name="user_search_history")
    op.drop_table("user_search_history")

    op.drop_index("ix_user_matches_user_id2", table_name="user_matches")
    op.drop_index("ix_user_matches_user_id1", table_name="user_matches")
    op.drop_table("user_matches")

    op.drop_index("ix_animal_likes_animal_id", table_name="animal_likes")
    op.drop_index("ix_animal_likes_from_user_id", table_name="animal_likes")
    op.drop_table("animal_likes")

    op.drop_index("ix_email_verification_codes_email_purpose", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")

    op.drop_index("idx_animal_photos_animal_id", table_name="animal_photos")
    op.drop_table("animal_photos")

    op.drop_index("idx_animals_species", table_name="animals")
    op.drop_index("idx_animals_status", table_name="animals")
    op.drop_index("idx_animals_owner", table_name="animals")
    op.drop_table("animals")

    op.drop_index("idx_user_sessions_refresh_hash", table_name="user_sessions")
    op.drop_index("idx_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("idx_user_devices_user_id", table_name="user_devices")
    op.drop_table("user_devices")

    op.drop_table("user_settings")
    op.drop_table("user_privacy_settings")

    op.drop_index("ix_user_profiles_location_lat_lon", table_name="user_profiles")
    op.drop_index("ix_user_profiles_location_city", table_name="user_profiles")
    op.drop_table("user_profiles")

    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")
