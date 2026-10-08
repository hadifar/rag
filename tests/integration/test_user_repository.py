"""Runs the user SQL against real Postgres (migrated with `alembic upgrade head`). Each
test works under its own throwaway user.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings
from rag.domain.models import RunSettingsUpdate, User
from rag.repository.user_repository import UserRepository


@pytest.fixture
async def pool(
    integration_settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        yield pool


@pytest.fixture
async def user(pool: AsyncConnectionPool[AsyncConnection]) -> AsyncGenerator[User]:
    repository = UserRepository(pool)
    user = await repository.create(f"user-test-{uuid.uuid4()}@example.com", "x")
    yield user
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (user.id,))


async def test_update_run_settings_sets_them_and_keeps_a_field_left_out(
    pool: AsyncConnectionPool[AsyncConnection], user: User
) -> None:
    repository = UserRepository(pool)
    assert (user.model, user.effort) == ("gpt-6-luna", "low")

    updated = await repository.update_run_settings(
        user.id, RunSettingsUpdate(model="gpt-6-sol", effort="high")
    )
    assert updated is not None
    assert (updated.model, updated.effort) == ("gpt-6-sol", "high")
    effort_only = await repository.update_run_settings(
        user.id, RunSettingsUpdate(effort="low")
    )
    assert effort_only is not None
    assert (effort_only.model, effort_only.effort) == ("gpt-6-sol", "low")
    assert await repository.get_by_id(user.id) == effort_only


async def test_update_run_settings_of_a_missing_user_returns_none(
    pool: AsyncConnectionPool[AsyncConnection],
) -> None:
    repository = UserRepository(pool)

    assert (
        await repository.update_run_settings(uuid.uuid4(), RunSettingsUpdate()) is None
    )
