"""rename the guards' names: 'restrict' to 'off_topic', 'verification' to 'answer_check'

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-08

The input guard's off-topic decision is now 'off_topic'. Cached verdicts are dropped:
they are keyed by the guard's old prompt, so none would be hit again. Saved answers'
`verification` events are now `answer_check` events, so their history still reads.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_decisions(old_constraint: str, new_constraint: str, decisions: str) -> None:
    op.execute("TRUNCATE input_verdict_cache")
    op.execute(f"ALTER TABLE input_verdict_cache DROP CONSTRAINT {old_constraint}")
    op.execute(
        f"""
        ALTER TABLE input_verdict_cache
            ADD CONSTRAINT {new_constraint} CHECK (decision IN ({decisions}))
        """
    )


def _rename_event(old_type: str, new_type: str) -> None:
    """Renames each `old_type` event of every answer, keeping the events' order."""
    op.execute(
        f"""
        UPDATE conversation_turns
        SET answer = (
            SELECT jsonb_agg(
                CASE WHEN e ->> 'type' = '{old_type}'
                    THEN jsonb_set(e, '{{type}}', '"{new_type}"')
                    ELSE e
                END
                ORDER BY i
            )
            FROM jsonb_array_elements(answer) WITH ORDINALITY AS events (e, i)
        )
        WHERE answer @> '[{{"type": "{old_type}"}}]'
        """
    )


def upgrade() -> None:
    _set_decisions(
        "input_verdict_cache_decision_check",
        "ck_input_verdict_cache_decision",
        "'allow', 'off_topic', 'block'",
    )
    _rename_event("verification", "answer_check")


def downgrade() -> None:
    _rename_event("answer_check", "verification")
    _set_decisions(
        "ck_input_verdict_cache_decision",
        "input_verdict_cache_decision_check",
        "'allow', 'restrict', 'block'",
    )
