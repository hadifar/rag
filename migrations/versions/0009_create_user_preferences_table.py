"""create user_preferences table, and copy the preferences out of LangGraph's store

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-02

Preferences were items in LangGraph's store (`langgraph.store`, prefix
`users.<user id>.preferences`), with no link to `users`. They're ours now: a table with a
foreign key, so a user's preferences go with them, and their rules as constraints. The
store's rows are left as they were, so the previous release still finds them if it's
rolled back to.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# rag.domain.models' MAX_PREFERENCES and MAX_PREFERENCE_LENGTH when this was written;
# changing either takes a new migration.
_MAX_PREFERENCES = 20
_MAX_PREFERENCE_LENGTH = 200


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE user_preferences (
            id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{{32}}$'),
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            -- Never blank, trimmed, capped (the service also collapses inner spaces).
            text text NOT NULL CONSTRAINT ck_user_preferences_text CHECK (
                text <> ''
                AND text = btrim(text)
                AND char_length(text) <= {_MAX_PREFERENCE_LENGTH}
            ),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # One of each per user, ignoring case; listed oldest first.
    op.execute(
        "CREATE UNIQUE INDEX ux_user_preferences_text "
        "ON user_preferences (user_id, lower(text))"
    )
    op.execute(
        "CREATE INDEX ix_user_preferences_user "
        "ON user_preferences (user_id, created_at)"
    )

    # Rows the old code couldn't have written (or of deleted users) are skipped rather
    # than failing the migration; duplicates keep the first.
    op.execute(
        f"""
        DO $$ BEGIN
            IF to_regclass('langgraph.store') IS NOT NULL THEN
                INSERT INTO user_preferences (id, user_id, text, created_at)
                SELECT key, user_id, text, created_at FROM (
                    SELECT s.key, u.id AS user_id, s.created_at,
                           btrim(s.value ->> 'text') AS text
                    FROM langgraph.store AS s
                    JOIN users AS u ON u.id::text = split_part(s.prefix, '.', 2)
                    WHERE s.prefix ~ '^users[.][0-9a-f-]{{36}}[.]preferences$'
                ) AS legacy
                WHERE key ~ '^[0-9a-f]{{32}}$'
                  AND text <> ''
                  AND char_length(text) <= {_MAX_PREFERENCE_LENGTH}
                ORDER BY created_at
                ON CONFLICT DO NOTHING;
            END IF;
        END $$
        """
    )

    # The cap, checked by Postgres itself. After the copy, which the old code already
    # kept under it. Locking the user's row makes two inserts racing for one user count
    # one after the other, so neither can slip past it.
    op.execute(
        f"""
        CREATE FUNCTION user_preferences_cap() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM 1 FROM users WHERE id = NEW.user_id FOR UPDATE;
            IF (SELECT count(*) FROM user_preferences WHERE user_id = NEW.user_id)
                    >= {_MAX_PREFERENCES} THEN
                RAISE EXCEPTION 'a user can keep at most {_MAX_PREFERENCES} preferences'
                    USING ERRCODE = 'check_violation',
                          CONSTRAINT = 'ck_user_preferences_cap';
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER tr_user_preferences_cap BEFORE INSERT ON user_preferences "
        "FOR EACH ROW EXECUTE FUNCTION user_preferences_cap()"
    )


def downgrade() -> None:
    op.execute("DROP TABLE user_preferences")
    op.execute("DROP FUNCTION user_preferences_cap()")
