"""drop LangGraph's store tables, unused since preferences moved out of them

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-04

The store (`langgraph.store`, and `store_migrations`, its record of its own setup) only
ever held preferences, which 0009 copied into `user_preferences`. Nothing opens it since.
The checkpointer's tables in the same schema are left alone. Not undone by downgrade:
no code at 0010 reads the store either.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS langgraph.store, langgraph.store_migrations")


def downgrade() -> None:
    pass
