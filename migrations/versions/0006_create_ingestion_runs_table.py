"""create ingestion_runs table: one row per knowledge-base upload

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-28

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ingestion_runs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            status text NOT NULL
                CHECK (status IN ('running', 'succeeded', 'failed')),
            archive_name text NOT NULL,
            created_by uuid REFERENCES users (id) ON DELETE SET NULL,
            started_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz,
            added integer,
            updated integer,
            unchanged integer,
            removed integer,
            chunks integer,
            error text
        )
        """
    )
    # At most one running ingestion, enforced by Postgres itself (so two uploads racing,
    # even on different instances, can't both start): a second insert fails.
    op.execute(
        "CREATE UNIQUE INDEX ux_ingestion_runs_one_running "
        "ON ingestion_runs ((true)) WHERE status = 'running'"
    )
    op.execute("CREATE INDEX ix_ingestion_runs_started ON ingestion_runs (started_at)")


def downgrade() -> None:
    op.execute("DROP TABLE ingestion_runs")
