"""add integrity constraints, and bring databases from before 0002's edit up to date

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINTS = {
    # Stored lowercase, so the unique email is unique regardless of case.
    "users": ("ck_users_email_lowercase", "email = lower(email)"),
    # A conversation is untitled (NULL) only while empty; a title is never blank.
    "conversations": ("ck_conversations_title_not_blank", "title <> ''"),
    "documents": (
        "ck_documents_content_hash_sha256",
        "content_hash ~ '^[0-9a-f]{64}$'",
    ),
    "chunks": ("ck_chunks_chunk_index_non_negative", "chunk_index >= 0"),
    # Each status has exactly the fields it should: counts only once it succeeded, an
    # error only once it failed, and a finish time once it's no longer running.
    "ingestion_runs": (
        "ck_ingestion_runs_state",
        """
        CASE status
            WHEN 'running' THEN finished_at IS NULL AND error IS NULL
                AND num_nulls(added, updated, unchanged, removed, chunks) = 5
            WHEN 'succeeded' THEN finished_at IS NOT NULL AND error IS NULL
                AND num_nulls(added, updated, unchanged, removed, chunks) = 0
            WHEN 'failed' THEN finished_at IS NOT NULL AND error IS NOT NULL
                AND num_nulls(added, updated, unchanged, removed, chunks) = 5
        END
        """,
    ),
}


def upgrade() -> None:
    # 0002 was edited in place before migrations became append-only. A database created
    # before that edit still has a NOT NULL title and lacks the one-empty-conversation
    # index; both statements are no-ops where 0002 already did this.
    op.execute("ALTER TABLE conversations ALTER COLUMN title DROP NOT NULL")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_conversations_one_empty_per_user "
        "ON conversations (user_id) WHERE title IS NULL"
    )

    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")
    for table, (name, check) in _CONSTRAINTS.items():
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({check})")


def downgrade() -> None:
    # Lowercased emails stay lowercase, and 0002's schema stays: both are 0002's now.
    for table, (name, _check) in _CONSTRAINTS.items():
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
