import uuid
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb
from pydantic import TypeAdapter

from rag.domain.errors import ConversationNotFoundError
from rag.domain.models import (
    AgentMemory,
    Attachment,
    Conversation,
    ConversationUpdate,
    StreamEvent,
    TaggedStreamEvent,
    Turn,
)
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, user_id, title, created_at, updated_at, pinned_at"
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

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._fetch_one(
            f"SELECT {_COLUMNS} FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        return _owned(conversation, conversation_id)

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
                WHERE user_id = %s AND pinned_at IS NULL
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
            WHERE user_id = %s AND pinned_at IS NULL AND (updated_at, id) < (%s, %s)
            ORDER BY updated_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, *before, limit),
        )

    async def list_pinned(self, user_id: uuid.UUID) -> list[Conversation]:
        return await self._fetch_all(
            f"""
            SELECT {_COLUMNS} FROM conversations
            WHERE user_id = %s AND pinned_at IS NOT NULL
            ORDER BY pinned_at DESC, id DESC
            """,
            (user_id,),
        )

    async def update_owned(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        change: ConversationUpdate,
    ) -> Conversation:
        conversation = await self._fetch_one(
            f"""
            UPDATE conversations SET
                title = COALESCE(%(title)s::text, title),
                pinned_at = CASE
                    WHEN %(pinned)s::boolean IS NULL THEN pinned_at
                    WHEN %(pinned)s::boolean THEN COALESCE(pinned_at, now())
                    ELSE NULL
                END
            WHERE id = %(id)s AND user_id = %(user_id)s
            RETURNING {_COLUMNS}
            """,
            {
                **asdict(change),
                "id": conversation_id,
                "user_id": user_id,
            },
        )
        return _owned(conversation, conversation_id)

    async def touch_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._fetch_one(
            f"""
            UPDATE conversations SET updated_at = now()
            WHERE id = %s AND user_id = %s
            RETURNING {_COLUMNS}
            """,
            (conversation_id, user_id),
        )
        return _owned(conversation, conversation_id)

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
        attachment_ids: Sequence[uuid.UUID] = (),
    ) -> None:
        # One transaction: a turn is never saved without the attachments it was sent with.
        async with self._pool.connection() as conn, conn.transaction():
            cur = await conn.execute(
                "INSERT INTO conversation_turns "
                "(conversation_id, question, answer, agent_messages) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (
                    conversation_id,
                    question,
                    Jsonb(_EVENTS.dump_python(answer, mode="json")),
                    Jsonb(memory) if memory is not None else None,
                ),
            )
            row = await cur.fetchone()
            assert row is not None  # an INSERT ... RETURNING always returns it
            if attachment_ids:
                # Only the conversation's own attachments: unnest keeps their order.
                await conn.execute(
                    """
                    INSERT INTO conversation_turn_attachments
                        (turn_id, attachment_id, position)
                    SELECT %s, a.id, (ids.ord - 1)::smallint
                    FROM unnest(%s::uuid[]) WITH ORDINALITY AS ids (id, ord)
                    JOIN conversation_attachments a ON a.id = ids.id
                    WHERE a.conversation_id = %s
                    """,
                    (row[0], list(attachment_ids), conversation_id),
                )

    async def list_turns(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[Turn]:
        # Raw rows: the _fetch_* helpers map onto Conversation, not Turn.
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id, question, answer, agent_messages FROM conversation_turns "
                "WHERE conversation_id = %s ORDER BY id LIMIT %s",  # LIMIT NULL: all
                (conversation_id, limit),
            )
            rows: list[tuple[int, str, Any, AgentMemory | None]] = await cur.fetchall()
            cur = await conn.execute(
                """
                SELECT ta.turn_id, a.id, a.conversation_id, a.name, a.media_type,
                    a.size, a.sha256, a.created_at
                FROM conversation_turn_attachments ta
                JOIN conversation_attachments a ON a.id = ta.attachment_id
                WHERE ta.turn_id = ANY(%s)
                ORDER BY ta.turn_id, ta.position
                """,
                ([row[0] for row in rows],),
            )
            attachments: dict[int, list[Attachment]] = {}
            for turn_id, *attachment in await cur.fetchall():
                attachments.setdefault(turn_id, []).append(Attachment(*attachment))
        return [
            Turn(
                question=question,
                answer=_EVENTS.validate_python(answer),
                memory=memory,
                attachments=attachments.get(turn_id, []),
            )
            for turn_id, question, answer, memory in rows
        ]


def _owned(
    conversation: Conversation | None, conversation_id: uuid.UUID
) -> Conversation:
    """The row a `*_owned` query found; missing and another user's raise the same."""
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    return conversation
