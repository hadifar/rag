"""add conversations.model and .effort: what a conversation's turns run on

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-07

The user picks them in the composer; the model is the one the provider is called with
(for Azure, a deployment). Existing conversations get the defaults.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE conversations
            ADD COLUMN model text NOT NULL DEFAULT 'gpt-6-luna'
                CONSTRAINT ck_conversations_model
                CHECK (model IN ('gpt-6-luna', 'gpt-6-astra', 'gpt-6-sol')),
            ADD COLUMN effort text NOT NULL DEFAULT 'low'
                CONSTRAINT ck_conversations_effort
                CHECK (effort IN ('low', 'medium', 'max'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE conversations DROP COLUMN model, DROP COLUMN effort")
