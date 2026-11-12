"""Align timestamp indexes with the workspace models."""

from alembic import op

revision = "20261112_0005"
down_revision = "20261112_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_index("ix_messages_updated_at", "messages", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_updated_at", table_name="messages")
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
