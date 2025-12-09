# alembic/versions/XXXXXXXX_add_likes_and_matches.py

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2025_12_09_add_likes_and_matches"
down_revision: Union[str, None] = "2025_12_09_add_thumb_url_to_animal_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "animal_likes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("from_user_id", sa.BigInteger(), nullable=False),
        sa.Column("animal_id", sa.BigInteger(), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["animal_id"],
            ["animals.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "from_user_id",
            "animal_id",
            name="uq_animal_likes_from_user_animal",
        ),
    )

    op.create_index(
        "ix_animal_likes_from_user_id",
        "animal_likes",
        ["from_user_id"],
    )
    op.create_index(
        "ix_animal_likes_animal_id",
        "animal_likes",
        ["animal_id"],
    )

    op.create_table(
        "user_matches",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id1", sa.BigInteger(), nullable=False),
        sa.Column("user_id2", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id1"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id2"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id1",
            "user_id2",
            name="uq_user_matches_pair",
        ),
    )

    op.create_index(
        "ix_user_matches_user_id1",
        "user_matches",
        ["user_id1"],
    )
    op.create_index(
        "ix_user_matches_user_id2",
        "user_matches",
        ["user_id2"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_matches_user_id2", table_name="user_matches")
    op.drop_index("ix_user_matches_user_id1", table_name="user_matches")
    op.drop_table("user_matches")

    op.drop_index("ix_animal_likes_animal_id", table_name="animal_likes")
    op.drop_index("ix_animal_likes_from_user_id", table_name="animal_likes")
    op.drop_table("animal_likes")
