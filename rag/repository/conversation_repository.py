import uuid
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb
from pydantic import TypeAdapter

from rag.domain.models import (
    AgentMemory,
    Conversation,
    StreamEvent,
    TaggedStreamEvent,
    Turn,
)
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, user_id, title, created_at, updated_at"
# Turn events are stored as the JSON objects their `type` tells apart.
_EVENTS = TypeAdapter(list[TaggedStreamEvent])


class ConversationRepository(BaseRepository[Conversation]):
    row_type = Conversation

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

    async def append_turn(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: list[StreamEvent],
        memory: AgentMemory | None = None,
    ) -> None:
        await self._execute(
            "INSERT INTO conversation_turns "
            "(conversation_id, question, answer, agent_messages) "
            "VALUES (%s, %s, %s, %s)",
            (
                conversation_id,
                question,
                Jsonb(_EVENTS.dump_python(answer, mode="json")),
                Jsonb(memory) if memory is not None else None,
            ),
        )

    async def list_turns(self, conversation_id: uuid.UUID) -> list[Turn]:
        # Raw rows: the _fetch_* helpers map onto Conversation, not Turn.
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT question, answer, agent_messages FROM conversation_turns "
                "WHERE conversation_id = %s ORDER BY id",
                (conversation_id,),
            )
            rows: list[tuple[str, Any, AgentMemory | None]] = await cur.fetchall()
        return [
            Turn(
                question=question,
                answer=_EVENTS.validate_python(answer),
                memory=memory,
            )
            for question, answer, memory in rows
        ]
