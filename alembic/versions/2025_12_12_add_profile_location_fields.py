"""add structured location fields to profiles

Revision ID: 2025_12_12_add_profile_location_fields
Revises: <PUT_PREVIOUS_REVISION_ID_HERE>
Create Date: 2025-12-12
"""

from alembic import op
import sqlalchemy as sa


revision = "2025_12_12_add_profile_location_fields"
down_revision = "2025_12_10_add_user_search_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("location_formatted", sa.String(length=256), nullable=True))
    op.add_column("user_profiles", sa.Column("location_city", sa.String(length=128), nullable=True))
    op.add_column("user_profiles", sa.Column("location_state", sa.String(length=128), nullable=True))
    op.add_column("user_profiles", sa.Column("location_country", sa.String(length=128), nullable=True))
    op.add_column("user_profiles", sa.Column("location_postcode", sa.String(length=32), nullable=True))

    op.add_column("user_profiles", sa.Column("location_lat", sa.Numeric(9, 6), nullable=True))
    op.add_column("user_profiles", sa.Column("location_lon", sa.Numeric(9, 6), nullable=True))

    op.add_column("user_profiles", sa.Column("location_result_type", sa.String(length=64), nullable=True))
    op.add_column("user_profiles", sa.Column("location_confidence", sa.Numeric(4, 3), nullable=True))

    op.create_index("ix_user_profiles_location_city", "user_profiles", ["location_city"])
    op.create_index("ix_user_profiles_location_lat_lon", "user_profiles", ["location_lat", "location_lon"])


def downgrade() -> None:
    op.drop_index("ix_user_profiles_location_lat_lon", table_name="user_profiles")
    op.drop_index("ix_user_profiles_location_city", table_name="user_profiles")

    op.drop_column("user_profiles", "location_confidence")
    op.drop_column("user_profiles", "location_result_type")

    op.drop_column("user_profiles", "location_lon")
    op.drop_column("user_profiles", "location_lat")

    op.drop_column("user_profiles", "location_postcode")
    op.drop_column("user_profiles", "location_country")
    op.drop_column("user_profiles", "location_state")
    op.drop_column("user_profiles", "location_city")
    op.drop_column("user_profiles", "location_formatted")