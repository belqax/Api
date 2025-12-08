"""Make users.phone nullable

Revision ID: 7c3f3f2b1a23
Revises: <put_your_previous_revision_here>
Create Date: 2025-12-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# ЗАМЕНИТЬ на реальные значения
revision = "2025_12_09_make_users_phone_nullable"
down_revision = "2025_12_08_add_is_superuser_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Делает колонку users.phone допускающей NULL.
    Уникальность и индекс остаются.
    """
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=32),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    """
    Возвращает NOT NULL для users.phone.

    ВАЖНО: перед откатом гарантировать, что в таблице нет записей
    с phone IS NULL, иначе откат не пройдёт.
    """
    # Явно проверяет наличие NULL и, если они есть, роняет откат с понятным текстом.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE phone IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade: some users have NULL phone';
            END IF;
        END;
        $$;
        """
    )

    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=32),
        nullable=False,
        existing_nullable=True,
    )
