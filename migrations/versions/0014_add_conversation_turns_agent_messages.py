"""add conversation_turns.agent_messages: what the chat agent remembers of each turn

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-06

The agent's memory of a conversation was LangGraph's checkpointed thread. It's now kept
beside each turn: the agent's own messages for it (the question, its tool calls and
their results, its answers), NULL for a turn it forgot (blocked, failed, cut short).
Past turns aren't carried over from the checkpointer: they stay NULL, so the agent
starts those conversations afresh.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE conversation_turns
        ADD COLUMN agent_messages jsonb
            CONSTRAINT ck_conversation_turns_agent_messages_array
            CHECK (jsonb_typeof(agent_messages) = 'array')
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE conversation_turns DROP COLUMN agent_messages")
