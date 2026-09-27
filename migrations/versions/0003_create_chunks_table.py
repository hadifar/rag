"""create chunks table (pgvector + full-text) for retrieval

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # vector(1536) must match rag/adapters/llm_client.py's EMBEDDING_DIMENSIONS.
    # content_tsv is the keyword half of hybrid search, kept in sync by Postgres itself.
    op.execute(
        """
        CREATE TABLE chunks (
            id text PRIMARY KEY,
            source_id text NOT NULL,
            chunk_index integer NOT NULL,
            content text NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            embedding vector(1536) NOT NULL,
            content_tsv tsvector
                GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
        )
        """
    )
    op.execute("CREATE INDEX ix_chunks_source ON chunks (source_id, chunk_index)")
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("CREATE INDEX ix_chunks_content_tsv ON chunks USING gin (content_tsv)")


def downgrade() -> None:
    # The extension stays: other objects may depend on it, and it's harmless unused.
    op.execute("DROP TABLE chunks")
