"""Runs the transcript SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under its own throwaway user; deleting it cascades to its conversations,
and from them to their turns.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import (
    ArtifactsReady,
    ReasoningDelta,
    SourceArtifact,
    TextDelta,
    Todo,
    TodosUpdated,
    ToolCall,
    Turn,
)
from rag.repository.conversation_repository import ConversationRepository
from rag.repository.transcript_repository import TranscriptRepository


@pytest.fixture
async def conversation_id(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[uuid.UUID]:
    async with db_pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, 'x') RETURNING id",
            (f"transcript-test-{uuid.uuid4()}@example.com",),
        )
        row = await cur.fetchone()
    assert row is not None
    conversation = await ConversationRepository(db_pool).get_or_create_empty(row[0])
    yield conversation.id
    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (row[0],))


async def test_turns_read_back_in_order_with_every_kind_of_event(
    db_pool: AsyncConnectionPool[AsyncConnection], conversation_id: uuid.UUID
) -> None:
    transcript = TranscriptRepository(db_pool)
    answer = [
        ReasoningDelta("Thinking"),
        TodosUpdated(todos=[Todo(content="Find it", status="completed")]),
        ToolCall(name="search_kb", status="pending", query="pricing"),
        ToolCall(name="search_kb", status="done", output="facts"),
        TextDelta("It costs 10."),
        ArtifactsReady(artifacts=[SourceArtifact(id="pricing.md")]),
    ]

    await transcript.append_turn(conversation_id, "How much?", answer)
    await transcript.append_turn(conversation_id, "thanks", [])

    assert await transcript.list_turns(conversation_id) == [
        Turn("How much?", answer),
        Turn("thanks", []),
    ]
    assert await transcript.list_turns(uuid.uuid4()) == []


async def test_turns_go_with_their_conversation(
    db_pool: AsyncConnectionPool[AsyncConnection], conversation_id: uuid.UUID
) -> None:
    transcript = TranscriptRepository(db_pool)
    await transcript.append_turn(conversation_id, "hi", [TextDelta("hello")])

    await ConversationRepository(db_pool).delete(conversation_id)

    assert await transcript.list_turns(conversation_id) == []
