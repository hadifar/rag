"""add chunks.summary_embedding, the embedding of the chunk's document summary

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-04

Nullable: chunks ingested before this, or from a document without a summary, have
none, and search falls back to the text embedding for them. `rag ingest --force`
fills it in for existing chunks.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # vector(1536) matches chunks.embedding.
    op.execute("ALTER TABLE chunks ADD COLUMN summary_embedding vector(1536)")


def downgrade() -> None:
    op.execute("ALTER TABLE chunks DROP COLUMN summary_embedding")
