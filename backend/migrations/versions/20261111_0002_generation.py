"""Add approval-gated project generations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0002"
down_revision: str | None = "20261111_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_generations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="staged"),
        sa.Column("manifest", sa.Text(), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_project_generations_project_id", "project_generations", ["project_id"])
    op.create_index("ix_project_generations_updated_at", "project_generations", ["updated_at"])


def downgrade() -> None:
    op.drop_table("project_generations")
