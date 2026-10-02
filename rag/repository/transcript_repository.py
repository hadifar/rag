import uuid
from typing import Any

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool
from pydantic import TypeAdapter

from rag.domain.models import StreamEvent, TaggedStreamEvent, Turn

# Events are stored as the JSON objects their `type` tells apart.
_EVENTS = TypeAdapter(list[TaggedStreamEvent])


class TranscriptRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]):
        self._pool = pool

    async def append_turn(
        self, conversation_id: uuid.UUID, question: str, answer: list[StreamEvent]
    ) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO conversation_turns (conversation_id, question, answer) "
                "VALUES (%s, %s, %s)",
                (
                    conversation_id,
                    question,
                    Jsonb(_EVENTS.dump_python(answer, mode="json")),
                ),
            )

    async def list_turns(self, conversation_id: uuid.UUID) -> list[Turn]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT question, answer FROM conversation_turns "
                "WHERE conversation_id = %s ORDER BY id",
                (conversation_id,),
            )
            rows: list[tuple[str, Any]] = await cur.fetchall()
        return [
            Turn(question=question, answer=_EVENTS.validate_python(answer))
            for question, answer in rows
        ]
