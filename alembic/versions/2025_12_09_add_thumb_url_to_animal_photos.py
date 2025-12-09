from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2025_12_09_add_thumb_url_to_animal_photos"
down_revision: Union[str, None] = "2025_12_09_make_users_phone_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "animal_photos",
        sa.Column("thumb_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("animal_photos", "thumb_url")
