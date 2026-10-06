"""drop the user_preferences table, unused since the preferences feature was removed

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-06

Nothing reads or writes a user's preferences any more: the chat agent no longer applies
them and the API no longer serves them. Downgrade brings back the table as 0009 made it,
with its constraints and cap, but empty: the preferences themselves are gone.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 0009's MAX_PREFERENCES and MAX_PREFERENCE_LENGTH, which downgrade restores.
_MAX_PREFERENCES = 20
_MAX_PREFERENCE_LENGTH = 200


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_preferences")
    op.execute("DROP FUNCTION IF EXISTS user_preferences_cap()")


def downgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE user_preferences (
            id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{{32}}$'),
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            text text NOT NULL CONSTRAINT ck_user_preferences_text CHECK (
                text <> ''
                AND text = btrim(text)
                AND char_length(text) <= {_MAX_PREFERENCE_LENGTH}
            ),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_user_preferences_text "
        "ON user_preferences (user_id, lower(text))"
    )
    op.execute(
        "CREATE INDEX ix_user_preferences_user "
        "ON user_preferences (user_id, created_at)"
    )
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
