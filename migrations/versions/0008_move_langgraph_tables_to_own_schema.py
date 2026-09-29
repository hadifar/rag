"""move LangGraph's checkpoint tables into their own `langgraph` schema

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-29

The tables belong to LangGraph (its checkpointer creates and migrates them); keeping them
out of `public` leaves `public` to the tables these migrations own. The app's checkpointer
connects with `search_path=langgraph` (rag/adapters/checkpointer.py).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "checkpoint_migrations",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
)


def _move(table: str, source: str, target: str) -> str:
    """Moves `table` if `source` has it. If the app already started with the new code, its
    checkpointer has created an empty copy in `target`: the rows are copied into that one.
    """
    return f"""
    DO $$ BEGIN
        IF to_regclass('{source}.{table}') IS NOT NULL THEN
            IF to_regclass('{target}.{table}') IS NULL THEN
                ALTER TABLE {source}.{table} SET SCHEMA {target};
            ELSE
                INSERT INTO {target}.{table} SELECT * FROM {source}.{table}
                    ON CONFLICT DO NOTHING;
                DROP TABLE {source}.{table};
            END IF;
        END IF;
    END $$
    """


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS langgraph")
    for table in _TABLES:
        op.execute(_move(table, "public", "langgraph"))


def downgrade() -> None:
    for table in _TABLES:
        op.execute(_move(table, "langgraph", "public"))
    op.execute("DROP SCHEMA IF EXISTS langgraph")
