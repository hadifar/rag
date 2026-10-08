"""add ingestion_runs.heartbeat_at: a running run's lease, renewed while it works

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-08

A run whose heartbeat stops (the process running it died) is failed once it goes
stale, so a sweep never fails a run another live worker or instance is still doing.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ingestion_runs "
        "ADD COLUMN heartbeat_at timestamptz NOT NULL DEFAULT now()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ingestion_runs DROP COLUMN heartbeat_at")
