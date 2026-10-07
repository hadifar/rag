"""add conversations pinned_at

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # When the user pinned it; null while it isn't pinned.
    op.add_column(
        "conversations",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Serves the sidebar's "Pinned" section: the user's pinned chats, last pinned first.
    op.create_index(
        "ix_conversations_user_pinned",
        "conversations",
        ["user_id", sa.text("pinned_at DESC"), sa.text("id DESC")],
        postgresql_where=sa.text("pinned_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_user_pinned", table_name="conversations")
    op.drop_column("conversations", "pinned_at")
