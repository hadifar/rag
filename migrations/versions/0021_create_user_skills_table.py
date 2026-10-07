"""create user_skills table: instructions a user saves for the agent to load

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-07

A skill is parsed from an uploaded SKILL.md: its frontmatter's `name` and
`description`, which the agent sees every turn, and its body, the instructions it
loads by name when a request fits the description. Uploading a skill under a name the
user already has replaces that one.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_skills (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            name text NOT NULL CHECK (name ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
            description text NOT NULL CHECK (description <> ''),
            instructions text NOT NULL CHECK (instructions <> ''),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ux_user_skills_name UNIQUE (user_id, name)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE user_skills")
