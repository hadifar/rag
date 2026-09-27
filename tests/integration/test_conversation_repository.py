"""Runs the conversation SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under its own throwaway user; deleting it cascades to its conversations.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings
from rag.repository.conversation_repository import ConversationRepository


@pytest.fixture
async def pool(
    integration_settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.AUTH.DATABASE_URL.get_secret_value(), open=False
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

    created = await repository.create(user_id, "first")
    assert await repository.get(created.id) == created

    touched = await repository.touch(created.id)
    assert touched is not None and touched.updated_at > created.updated_at

    await repository.set_title(created.id, "renamed")
    fetched = await repository.get(created.id)
    assert fetched is not None and fetched.title == "renamed"

    await repository.delete(created.id)
    assert await repository.get(created.id) is None
    assert await repository.touch(created.id) is None


async def test_keyset_pagination_visits_every_row_once_newest_first(
    pool: AsyncConnectionPool[AsyncConnection], user_id: uuid.UUID
) -> None:
    repository = ConversationRepository(pool)
    created = [await repository.create(user_id, f"chat {i}") for i in range(5)]
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
    conversation = await repository.create(user_id, "doomed")

    async with pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (user_id,))

    assert await repository.get(conversation.id) is None
