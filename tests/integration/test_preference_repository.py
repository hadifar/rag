"""Runs the preference SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under throwaway users; deleting one cascades to its preferences.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
from psycopg import AsyncConnection
from psycopg.errors import CheckViolation
from psycopg_pool import AsyncConnectionPool

from rag.domain.errors import TooManyPreferencesError
from rag.domain.models import MAX_PREFERENCES, Preference
from rag.repository.preference_repository import PreferenceRepository

NewUser = Callable[[], Awaitable[uuid.UUID]]


@pytest.fixture
async def new_user(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[NewUser]:
    created: list[uuid.UUID] = []

    async def create() -> uuid.UUID:
        async with db_pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO users (email, hashed_password) VALUES (%s, 'x') "
                "RETURNING id",
                (f"preference-test-{uuid.uuid4()}@example.com",),
            )
            row = await cur.fetchone()
        assert row is not None
        created.append(row[0])
        return row[0]

    yield create
    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = ANY(%s)", (created,))


def _preference(text: str) -> Preference:
    return Preference(id=uuid.uuid4().hex, text=text)


async def test_each_users_own_are_listed_oldest_first_and_deleted(
    db_pool: AsyncConnectionPool[AsyncConnection], new_user: NewUser
) -> None:
    repository = PreferenceRepository(db_pool)
    alice, bob = await new_user(), await new_user()
    first = await repository.add(alice, _preference("Answer in Dutch"))
    second = await repository.add(alice, _preference("Be brief"))

    assert await repository.list_for_user(alice) == [first, second]
    assert await repository.list_for_user(bob) == []
    assert not await repository.delete(bob, first.id)
    assert await repository.delete(alice, first.id)
    assert await repository.list_for_user(alice) == [second]


async def test_the_same_text_again_returns_the_one_there_is(
    db_pool: AsyncConnectionPool[AsyncConnection], new_user: NewUser
) -> None:
    repository = PreferenceRepository(db_pool)
    alice = await new_user()
    kept = await repository.add(alice, _preference("Answer in Dutch"))

    # As if two requests raced past the service's own check.
    assert await repository.add(alice, _preference("answer in dutch")) == kept
    assert await repository.list_for_user(alice) == [kept]


async def test_the_cap_holds_even_for_racing_inserts(
    db_pool: AsyncConnectionPool[AsyncConnection], new_user: NewUser
) -> None:
    repository = PreferenceRepository(db_pool)
    alice = await new_user()
    for i in range(MAX_PREFERENCES - 1):
        await repository.add(alice, _preference(f"preference {i}"))

    results = await asyncio.gather(
        repository.add(alice, _preference("one")),
        repository.add(alice, _preference("two")),
        return_exceptions=True,
    )

    assert sum(isinstance(r, TooManyPreferencesError) for r in results) == 1
    assert len(await repository.list_for_user(alice)) == MAX_PREFERENCES


async def test_untidy_text_is_rejected_by_the_table(
    db_pool: AsyncConnectionPool[AsyncConnection], new_user: NewUser
) -> None:
    alice = await new_user()

    with pytest.raises(CheckViolation):
        await PreferenceRepository(db_pool).add(alice, _preference(" padded "))


async def test_a_users_preferences_go_with_them(
    db_pool: AsyncConnectionPool[AsyncConnection], new_user: NewUser
) -> None:
    repository = PreferenceRepository(db_pool)
    alice = await new_user()
    await repository.add(alice, _preference("Answer in Dutch"))

    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (alice,))

    assert await repository.list_for_user(alice) == []
