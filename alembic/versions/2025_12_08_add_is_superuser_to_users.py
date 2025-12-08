from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2025_12_08_add_is_superuser_to_users"  # оставить как сгенерировал Alembic
down_revision: Union[str, None] = "2025_12_07_add_email_verification"  # ИЛИ твой фактический previous id
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # опционально убрать default на уровне схемы, если он не нужен:
    op.alter_column(
        "users",
        "is_superuser",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("users", "is_superuser")
