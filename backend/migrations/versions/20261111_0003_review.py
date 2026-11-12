"""Add staged code reviews and generated tests."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0003"
down_revision: str | None = "20261111_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("generation_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="staged"),
        sa.Column("report", sa.Text(), nullable=False),
        sa.Column("test_manifest", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_id"], ["project_generations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_generation_reviews_generation_id", "generation_reviews", ["generation_id"])
    op.create_index("ix_generation_reviews_updated_at", "generation_reviews", ["updated_at"])


def downgrade() -> None:
    op.drop_table("generation_reviews")
