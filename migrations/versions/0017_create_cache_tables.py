"""create cache tables: query embeddings, search results, input-guard verdicts

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-06

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("embedding_cache", "search_cache", "input_verdict_cache")


def upgrade() -> None:
    # UNLOGGED: cheaper writes, emptied after a crash, which a cache can afford. Each
    # row is keyed by the model that produced it and a sha256 of its input, so a new
    # model misses every older row. vector(1536) must match EMBEDDING_DIMENSIONS.
    op.execute(
        """
        CREATE UNLOGGED TABLE embedding_cache (
            model text NOT NULL,
            key bytea NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            PRIMARY KEY (model, key)
        )
        """
    )
    # A search's ranked chunk ids, not their text: a hit joins `chunks`, so it never
    # returns a chunk ingestion removed. Ingestion empties the table.
    op.execute(
        """
        CREATE UNLOGGED TABLE search_cache (
            model text NOT NULL,
            key bytea NOT NULL,
            chunk_ids text[] NOT NULL,
            scores float8[] NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            PRIMARY KEY (model, key),
            CONSTRAINT ck_search_cache_aligned
                CHECK (cardinality(chunk_ids) = cardinality(scores))
        )
        """
    )
    op.execute(
        """
        CREATE UNLOGGED TABLE input_verdict_cache (
            model text NOT NULL,
            key bytea NOT NULL,
            decision text NOT NULL
                CHECK (decision IN ('allow', 'restrict', 'block')),
            reason text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            PRIMARY KEY (model, key)
        )
        """
    )
    for table in _TABLES:
        op.execute(f"CREATE INDEX ix_{table}_expires ON {table} (expires_at)")


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP TABLE {table}")
