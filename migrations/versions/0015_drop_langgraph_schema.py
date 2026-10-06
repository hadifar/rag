"""drop the `langgraph` schema, unused since the agent's memory moved to conversation_turns

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-06

The schema held LangGraph's checkpointer tables (0008 moved them there), the chat agent's
memory before 0014 kept it beside each turn. Nothing opens them since. Downgrade brings
back the empty schema, not its data: no code at 0014 reads it either.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS langgraph CASCADE")


def downgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS langgraph")
