import uuid
from datetime import datetime

from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import Conversation

_COLUMNS = "id, user_id, title, created_at, updated_at"


class ConversationRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]):
        self._pool = pool

    async def create(self, user_id: uuid.UUID, title: str) -> Conversation:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(Conversation)) as cur,
        ):
            await cur.execute(
                f"""
                INSERT INTO conversations (user_id, title)
                VALUES (%s, %s)
                RETURNING {_COLUMNS}
                """,
                (user_id, title),
            )
            row = await cur.fetchone()
            assert row is not None  # INSERT ... RETURNING always yields a row
            return row

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(Conversation)) as cur,
        ):
            await cur.execute(
                f"SELECT {_COLUMNS} FROM conversations WHERE id = %s",
                (conversation_id,),
            )
            return await cur.fetchone()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(Conversation)) as cur,
        ):
            if before is None:
                await cur.execute(
                    f"""
                    SELECT {_COLUMNS} FROM conversations
                    WHERE user_id = %s
                    ORDER BY updated_at DESC, id DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
            else:
                # Row comparison matches the (updated_at DESC, id DESC) index order,
                # so ties on updated_at are neither skipped nor repeated across pages.
                await cur.execute(
                    f"""
                    SELECT {_COLUMNS} FROM conversations
                    WHERE user_id = %s AND (updated_at, id) < (%s, %s)
                    ORDER BY updated_at DESC, id DESC
                    LIMIT %s
                    """,
                    (user_id, *before, limit),
                )
            return await cur.fetchall()

    async def touch(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Bumps updated_at; None if the conversation was deleted meanwhile."""
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(Conversation)) as cur,
        ):
            await cur.execute(
                f"""
                UPDATE conversations SET updated_at = now()
                WHERE id = %s
                RETURNING {_COLUMNS}
                """,
                (conversation_id,),
            )
            return await cur.fetchone()

    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE conversations SET title = %s WHERE id = %s",
                (title, conversation_id),
            )

    async def delete(self, conversation_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "DELETE FROM conversations WHERE id = %s", (conversation_id,)
            )
