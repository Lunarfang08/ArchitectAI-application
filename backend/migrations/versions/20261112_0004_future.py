"""Add Future Lab simulations."""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0004"
down_revision = "20261111_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "future_simulations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario_type", sa.String(40), nullable=False),
        sa.Column("scenario_input", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_future_simulations_project_id", "future_simulations", ["project_id"])
    op.create_index("ix_future_simulations_updated_at", "future_simulations", ["updated_at"])


def downgrade() -> None:
    op.drop_table("future_simulations")
