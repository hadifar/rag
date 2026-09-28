import uuid
from datetime import datetime

from rag.domain.models import Conversation
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, user_id, title, created_at, updated_at"


class ConversationRepository(BaseRepository[Conversation]):
    row_type = Conversation

    async def create(
        self, user_id: uuid.UUID, title: str, conversation_id: uuid.UUID | None = None
    ) -> Conversation:
        conversation = await self._fetch_one(
            f"""
            INSERT INTO conversations (id, user_id, title)
            VALUES (%s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (conversation_id or uuid.uuid4(), user_id, title),
        )
        assert conversation is not None  # INSERT ... RETURNING always yields a row
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
