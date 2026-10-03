"""create conversation_turns table: what the user saw of each conversation; drop past ones

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-02

A conversation's history was rebuilt from the chat agent's checkpointed messages. It's
now its own record: each turn's question and the events its answer streamed. Past
conversations have no such record and aren't carried over: they're deleted, with their
checkpointed messages, which nothing could reach without them. Not undone by downgrade.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# LangGraph's checkpoint tables holding the threads' data (0008 moved them to its schema);
# its own checkpoint_migrations table is left alone.
_CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE conversation_turns (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            conversation_id uuid NOT NULL
                REFERENCES conversations (id) ON DELETE CASCADE,
            question text NOT NULL CHECK (question <> ''),
            -- The answer's stream events, each a JSON object tagged by its `type`.
            answer jsonb NOT NULL CHECK (jsonb_typeof(answer) = 'array'),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_conversation_turns_conversation "
        "ON conversation_turns (conversation_id, id)"
    )

    op.execute("DELETE FROM conversations")
    for table in _CHECKPOINT_TABLES:
        op.execute(
            f"""
            DO $$ BEGIN
                IF to_regclass('langgraph.{table}') IS NOT NULL THEN
                    TRUNCATE langgraph.{table};
                END IF;
            END $$
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE conversation_turns")
