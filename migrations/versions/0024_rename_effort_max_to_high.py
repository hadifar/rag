"""rename conversations.effort 'max' to 'high': the name the model takes it by

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-08

Conversations set to 'max' are moved to 'high'.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rename_effort(old: str, new: str) -> None:
    op.execute("ALTER TABLE conversations DROP CONSTRAINT ck_conversations_effort")
    op.execute(f"UPDATE conversations SET effort = '{new}' WHERE effort = '{old}'")
    op.execute(
        f"""
        ALTER TABLE conversations
            ADD CONSTRAINT ck_conversations_effort
            CHECK (effort IN ('low', 'medium', '{new}'))
        """
    )


def upgrade() -> None:
    _rename_effort("max", "high")


def downgrade() -> None:
    _rename_effort("high", "max")
