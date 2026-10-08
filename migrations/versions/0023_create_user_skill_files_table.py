"""create user_skill_files table: the reference files a skill was uploaded with

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-07

A skill uploaded as a .zip or .skill archive keeps the text files beside its SKILL.md,
by their path in the archive (e.g. `references/api.md`). The agent reads one by path
when the skill's instructions call for it. Uploading the skill again replaces them;
deleting it deletes them.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_skill_files (
            skill_id uuid NOT NULL REFERENCES user_skills (id) ON DELETE CASCADE,
            path text NOT NULL CHECK (path <> ''),
            content text NOT NULL,
            PRIMARY KEY (skill_id, path)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE user_skill_files")
