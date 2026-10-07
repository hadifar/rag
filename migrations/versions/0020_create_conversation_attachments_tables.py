"""create conversation_attachments tables: files the user attaches to their messages

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-07

A file is uploaded to its conversation first, then sent with a message: the turns it
went with are listed in conversation_turn_attachments (a failed turn's retry sends it
again). A message may be only its attachments, so a turn's question can be empty.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE conversation_attachments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id uuid NOT NULL
                REFERENCES conversations (id) ON DELETE CASCADE,
            name text NOT NULL CHECK (name <> ''),
            media_type text NOT NULL CHECK (media_type <> ''),
            -- Hex sha256 of `data`: keys the off-topic guard's cached verdicts.
            sha256 text NOT NULL CHECK (length(sha256) = 64),
            data bytea NOT NULL,
            size integer GENERATED ALWAYS AS (octet_length(data)) STORED,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_conversation_attachments_not_empty CHECK (octet_length(data) > 0)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_conversation_attachments_conversation "
        "ON conversation_attachments (conversation_id, created_at)"
    )
    op.execute(
        """
        CREATE TABLE conversation_turn_attachments (
            turn_id bigint NOT NULL
                REFERENCES conversation_turns (id) ON DELETE CASCADE,
            attachment_id uuid NOT NULL
                REFERENCES conversation_attachments (id) ON DELETE CASCADE,
            -- Its place among the turn's attachments, as the user sent them.
            position smallint NOT NULL CHECK (position >= 0),
            PRIMARY KEY (turn_id, attachment_id),
            CONSTRAINT ux_conversation_turn_attachments_position
                UNIQUE (turn_id, position)
        )
        """
    )
    # Finds whether an attachment was ever sent (an unsent one can be discarded).
    op.execute(
        "CREATE INDEX ix_conversation_turn_attachments_attachment "
        "ON conversation_turn_attachments (attachment_id)"
    )
    op.execute(
        "ALTER TABLE conversation_turns DROP CONSTRAINT conversation_turns_question_check"
    )


def downgrade() -> None:
    op.execute("DROP TABLE conversation_turn_attachments")
    op.execute("DROP TABLE conversation_attachments")
    # Attachment-only turns can't satisfy the restored check; they go.
    op.execute("DELETE FROM conversation_turns WHERE question = ''")
    op.execute(
        "ALTER TABLE conversation_turns ADD CONSTRAINT conversation_turns_question_check "
        "CHECK (question <> '')"
    )
