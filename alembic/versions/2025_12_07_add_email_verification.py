from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# заменишь на свои реальные ревизии
revision: str = "2025_12_07_add_email_verification"
down_revision: Union[str, None] = "2025_12_07_0001_initial_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # если колонка email уже существует в users – этот add_column убери
    op.add_column(
        "users",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "purpose",
            sa.String(length=32),
            nullable=False,
            server_default="register",
        ),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_email_verification_codes_email_purpose",
        "email_verification_codes",
        ["email", "purpose"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_codes_email_purpose",
        table_name="email_verification_codes",
    )
    op.drop_table("email_verification_codes")
    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "email")
