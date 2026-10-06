"""Runs the conversation SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under its own throwaway user; deleting it cascades to its conversations,
and from them to their turns.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings
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


@pytest.fixture
async def pool(
    integration_settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        yield pool


@pytest.fixture
async def user_id(
    pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[uuid.UUID]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, 'x') RETURNING id",
            (f"conversation-test-{uuid.uuid4()}@example.com",),
        )
        row = await cur.fetchone()
        assert row is not None
    yield row[0]
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (row[0],))


async def test_create_get_touch_title_delete(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)

    created = await repository.get_or_create_empty(user_id)
    assert created.title is None
    assert await repository.get_owned(user_id, created.id) == created
    # Still empty, so asking again returns the same row instead of a second one.
    assert (await repository.get_or_create_empty(user_id)).id == created.id

    touched = await repository.touch_owned(user_id, created.id)
    assert touched is not None
    assert touched.updated_at > created.updated_at

    await repository.set_title(created.id, "renamed")
    fetched = await repository.get_owned(user_id, created.id)
    assert fetched is not None
    assert fetched.title == "renamed"

    await repository.delete(created.id)
    assert await repository.get_owned(user_id, created.id) is None
    assert await repository.touch_owned(user_id, created.id) is None


async def test_another_users_conversation_is_not_found(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)
    conversation = await repository.get_or_create_empty(user_id)
    stranger = uuid.uuid4()

    assert await repository.get_owned(stranger, conversation.id) is None
    assert await repository.touch_owned(stranger, conversation.id) is None
    assert await repository.get_owned(user_id, conversation.id) == conversation


async def test_keyset_pagination_visits_every_row_once_newest_first(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)
    created = []
    for i in range(5):
        conversation = await repository.get_or_create_empty(user_id)
        await repository.set_title(conversation.id, f"chat {i}")  # frees the next one
        created.append(conversation)
    # Same updated_at for all: the id tiebreaker alone must keep pages disjoint.
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE conversations SET updated_at = '2026-01-01' WHERE user_id = %s",
            (user_id,),
        )

    seen, before = [], None
    while page := await repository.list_for_user(user_id, limit=2, before=before):
        seen.extend(page)
        before = (page[-1].updated_at, page[-1].id)

    assert sorted(c.id for c in seen) == sorted(c.id for c in created)
    assert [c.id for c in seen] == sorted((c.id for c in created), reverse=True)


async def test_deleting_a_user_deletes_their_conversations(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)
    conversation = await repository.get_or_create_empty(user_id)

    async with pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (user_id,))

    assert await repository.get_owned(user_id, conversation.id) is None


async def test_turns_read_back_in_order_with_every_kind_of_event(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)
    conversation = await repository.get_or_create_empty(user_id)
    answer = [
        ReasoningDelta("Thinking"),
        TodosUpdated(todos=[Todo(content="Find it", status="completed")]),
        ToolCall(name="search_kb", status="pending", query="pricing"),
        ToolCall(name="search_kb", status="done", output="facts"),
        TextDelta("It costs 10."),
        ArtifactsReady(artifacts=[SourceArtifact(id="pricing.md")]),
    ]

    memory = [{"type": "human", "data": {"content": "How much?"}}]

    await repository.append_turn(conversation.id, "How much?", answer, memory)
    await repository.append_turn(conversation.id, "thanks", [])

    assert await repository.list_turns(conversation.id) == [
        Turn("How much?", answer, memory),
        Turn("thanks", [], None),
    ]
    assert await repository.list_turns(uuid.uuid4()) == []


async def test_turns_go_with_their_conversation(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)
    conversation = await repository.get_or_create_empty(user_id)
    await repository.append_turn(conversation.id, "hi", [TextDelta("hello")])

    await repository.delete(conversation.id)

    assert await repository.list_turns(conversation.id) == []
