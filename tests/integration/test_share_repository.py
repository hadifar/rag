"""Runs the share SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under its own throwaway user; deleting it cascades to its
conversations, and from them to their turns and links.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings
from rag.domain.models import Conversation, TextDelta
from rag.repository.conversation_repository import ConversationRepository
from rag.repository.share_repository import ShareRepository


@pytest.fixture
async def pool(
    integration_settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        yield pool


@pytest.fixture
async def conversation(
    pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[Conversation]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, 'x') RETURNING id",
            (f"share-test-{uuid.uuid4()}@example.com",),
        )
        row = await cur.fetchone()
        assert row is not None
    yield await ConversationRepository(pool).get_or_create_empty(row[0])
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (row[0],))


async def test_a_conversation_without_turns_is_not_shared(
    pool: AsyncConnectionPool[AsyncConnection], conversation: Conversation
) -> None:
    shares = ShareRepository(pool)

    assert await shares.save(conversation.id, "title") is None
    assert await shares.get_for_conversation(conversation.id) is None


async def test_sharing_again_takes_a_new_snapshot_behind_the_same_link(
    pool: AsyncConnectionPool[AsyncConnection], conversation: Conversation
) -> None:
    conversations, shares = ConversationRepository(pool), ShareRepository(pool)
    await conversations.append_turn(conversation.id, "q1", [TextDelta(text="a1")])

    first = await shares.save(conversation.id, "before")
    assert first is not None
    assert first.turn_count == 1
    assert await shares.get(first.id) == first

    await conversations.append_turn(conversation.id, "q2", [TextDelta(text="a2")])
    again = await shares.save(conversation.id, "after")
    assert again is not None
    assert (again.id, again.title, again.turn_count) == (first.id, "after", 2)
    assert again.shared_at >= first.shared_at
    turns = await conversations.list_turns(conversation.id, first.turn_count)
    assert [t.question for t in turns] == ["q1"]


async def test_unsharing_or_deleting_the_conversation_takes_the_link_down(
    pool: AsyncConnectionPool[AsyncConnection], conversation: Conversation
) -> None:
    conversations, shares = ConversationRepository(pool), ShareRepository(pool)
    await conversations.append_turn(conversation.id, "q", [TextDelta(text="a")])

    share = await shares.save(conversation.id, "t")
    assert share is not None
    await shares.delete_for_conversation(conversation.id)
    assert await shares.get(share.id) is None

    reshared = await shares.save(conversation.id, "t")
    assert reshared is not None
    assert reshared.id != share.id  # a new link
    await conversations.delete(conversation.id)
    assert await shares.get(reshared.id) is None
