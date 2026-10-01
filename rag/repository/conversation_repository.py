import uuid
from datetime import datetime

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import Conversation, HistoryMessage
from rag.domain.ports import HistoryStorePort
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, user_id, title, created_at, updated_at"


class ConversationRepository(BaseRepository[Conversation]):
    row_type = Conversation

    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection],
        history: HistoryStorePort,
    ):
        super().__init__(pool)
        self._history = history

    async def get_or_create_empty(self, user_id: uuid.UUID) -> Conversation:
        # One statement, so two concurrent calls can't both create one: the second
        # hits ux_conversations_one_empty_per_user and gets the first's row back.
        conversation = await self._fetch_one(
            f"""
            INSERT INTO conversations (user_id) VALUES (%s)
            ON CONFLICT (user_id) WHERE title IS NULL
            DO UPDATE SET updated_at = now()
            RETURNING {_COLUMNS}
            """,
            (user_id,),
        )
        assert conversation is not None  # the INSERT or the UPDATE always returns it
        return conversation

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM conversations WHERE id = %s", (conversation_id,)
        )

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        if before is None:
            return await self._fetch_all(
                f"""
                SELECT {_COLUMNS} FROM conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
        # Row comparison matches the (updated_at DESC, id DESC) index order, so ties
        # on updated_at are neither skipped nor repeated across pages.
        return await self._fetch_all(
            f"""
            SELECT {_COLUMNS} FROM conversations
            WHERE user_id = %s AND (updated_at, id) < (%s, %s)
            ORDER BY updated_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, *before, limit),
        )

    async def touch(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Bumps updated_at; None if the conversation was deleted meanwhile."""
        return await self._fetch_one(
            f"""
            UPDATE conversations SET updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (conversation_id,),
        )

    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None:
        await self._execute(
            "UPDATE conversations SET title = %s WHERE id = %s",
            (title, conversation_id),
        )

    async def delete(self, conversation_id: uuid.UUID) -> None:
        await self._execute(
            "DELETE FROM conversations WHERE id = %s", (conversation_id,)
        )

    async def all_ids(self) -> set[uuid.UUID]:
        async with self._pool.connection() as conn:
            cur = await conn.execute("SELECT id FROM conversations")
            return {row[0] for row in await cur.fetchall()}

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        return await self._history.get_history(thread_id)

    async def delete_history(self, thread_id: str) -> None:
        await self._history.delete_history(thread_id)

    async def list_thread_ids(self) -> set[str]:
        return await self._history.list_thread_ids()
