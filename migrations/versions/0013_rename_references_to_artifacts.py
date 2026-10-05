"""rewrite saved answers' references events as artifacts events

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-05

A turn's references (`{"type": "references", "references": [<source id>, ...]}`) are
now its artifacts, each tagged by its kind: `{"type": "artifacts", "artifacts":
[{"kind": "source", "id": <source id>}, ...]}`. Saved answers are rewritten so their
history still reads. Downgrade turns source artifacts back into references; the only
kind there is yet.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rewrite(old_type: str, new_event: str) -> None:
    """Replaces each `old_type` event `e` of every answer with `new_event`, an SQL
    expression of `e`, keeping the events' order.
    """
    op.execute(
        f"""
        UPDATE conversation_turns
        SET answer = (
            SELECT jsonb_agg(
                CASE WHEN e ->> 'type' = '{old_type}' THEN {new_event} ELSE e END
                ORDER BY i
            )
            FROM jsonb_array_elements(answer) WITH ORDINALITY AS events (e, i)
        )
        WHERE answer @> '[{{"type": "{old_type}"}}]'
        """
    )


def upgrade() -> None:
    _rewrite(
        "references",
        """
        jsonb_build_object(
            'type', 'artifacts',
            'artifacts', COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object('kind', 'source', 'id', ref) ORDER BY j
                    )
                    FROM jsonb_array_elements_text(e -> 'references')
                        WITH ORDINALITY AS refs (ref, j)
                ),
                '[]'::jsonb
            )
        )
        """,
    )


def downgrade() -> None:
    _rewrite(
        "artifacts",
        """
        jsonb_build_object(
            'type', 'references',
            'references', COALESCE(
                (
                    SELECT jsonb_agg(a ->> 'id' ORDER BY j)
                    FROM jsonb_array_elements(e -> 'artifacts')
                        WITH ORDINALITY AS artifacts (a, j)
                    WHERE a ->> 'kind' = 'source'
                ),
                '[]'::jsonb
            )
        )
        """,
    )
