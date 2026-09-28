"""create documents table: one row per ingested document, owning its chunks

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # content_hash lets ingestion skip unchanged documents instead of re-embedding them.
    op.execute(
        """
        CREATE TABLE documents (
            source_id text PRIMARY KEY,
            content_hash text NOT NULL,
            ingested_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # Chunks ingested before this table existed get an empty hash, so the next
    # ingest treats them as changed and re-embeds them.
    op.execute(
        "INSERT INTO documents (source_id, content_hash) "
        "SELECT DISTINCT source_id, '' FROM chunks"
    )
    # Replacing or removing a document deletes its chunks with it.
    op.execute(
        "ALTER TABLE chunks ADD CONSTRAINT fk_chunks_document "
        "FOREIGN KEY (source_id) REFERENCES documents (source_id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE chunks DROP CONSTRAINT fk_chunks_document")
    op.execute("DROP TABLE documents")
