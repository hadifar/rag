"""move model and effort from conversations to users: one pick for all their chats

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-08

A user's pick now carries over to every conversation, new or old. Each user starts with
what their most recently used conversation was set to, or the defaults if they have
none. Downgrade sets every conversation of a user to that user's pick.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_columns(table: str) -> None:
    op.execute(
        f"""
        ALTER TABLE {table}
            ADD COLUMN model text NOT NULL DEFAULT 'gpt-6-luna'
                CONSTRAINT ck_{table}_model
                CHECK (model IN ('gpt-6-luna', 'gpt-6-astra', 'gpt-6-sol')),
            ADD COLUMN effort text NOT NULL DEFAULT 'low'
                CONSTRAINT ck_{table}_effort
                CHECK (effort IN ('low', 'medium', 'high'))
        """
    )


def upgrade() -> None:
    _add_columns("users")
    op.execute(
        """
        UPDATE users u SET model = c.model, effort = c.effort
        FROM (
            SELECT DISTINCT ON (user_id) user_id, model, effort FROM conversations
            ORDER BY user_id, updated_at DESC, id DESC
        ) c
        WHERE c.user_id = u.id
        """
    )
    op.execute("ALTER TABLE conversations DROP COLUMN model, DROP COLUMN effort")


def downgrade() -> None:
    _add_columns("conversations")
    op.execute(
        """
        UPDATE conversations c SET model = u.model, effort = u.effort
        FROM users u WHERE u.id = c.user_id
        """
    )
    op.execute("ALTER TABLE users DROP COLUMN model, DROP COLUMN effort")
