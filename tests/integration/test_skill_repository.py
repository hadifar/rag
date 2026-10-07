"""Runs the skill SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under its own throwaway users; deleting them cascades to their skills
and their skills' files.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg.errors import CheckViolation
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import SkillContent
from rag.repository.skill_repository import SkillRepository


@pytest.fixture
async def users(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[tuple[uuid.UUID, uuid.UUID]]:
    ids: list[uuid.UUID] = []
    async with db_pool.connection() as conn:
        for _ in range(2):
            cur = await conn.execute(
                "INSERT INTO users (email, hashed_password) VALUES (%s, 'x') "
                "RETURNING id",
                (f"skill-test-{uuid.uuid4()}@example.com",),
            )
            row = await cur.fetchone()
            assert row is not None
            ids.append(row[0])
    yield ids[0], ids[1]
    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = ANY(%s)", (ids,))


async def test_saving_a_skill_of_the_same_name_replaces_it(
    db_pool: AsyncConnectionPool[AsyncConnection],
    users: tuple[uuid.UUID, uuid.UUID],
) -> None:
    skills, (alice, _) = SkillRepository(db_pool), users
    first = await skills.save(
        alice, "notes", "Old.", "old instructions", {"old.md": "o", "kept.md": "k1"}
    )

    second = await skills.save(
        alice, "notes", "New.", "new instructions", {"kept.md": "k2"}
    )

    assert first.file_count == 2
    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.updated_at > first.updated_at
    assert second.file_count == 1
    assert await skills.list_for_user(alice) == [second]
    assert await skills.get_content(alice, "notes") == SkillContent(
        "new instructions", files=("kept.md",)
    )
    assert await skills.get_file(alice, "notes", "old.md") is None
    assert await skills.get_file(alice, "notes", "kept.md") == "k2"


async def test_a_users_skills_are_theirs_alone(
    db_pool: AsyncConnectionPool[AsyncConnection],
    users: tuple[uuid.UUID, uuid.UUID],
) -> None:
    skills, (alice, bob) = SkillRepository(db_pool), users
    skill = await skills.save(alice, "notes", "Notes.", "instructions", {"a.md": "A"})
    await skills.save(bob, "notes", "Bob's.", "bob's instructions", {"b.md": "B"})

    assert [s.description for s in await skills.list_for_user(alice)] == ["Notes."]
    assert await skills.get_content(bob, "notes") == SkillContent(
        "bob's instructions", files=("b.md",)
    )
    assert await skills.get_file(bob, "notes", "a.md") is None
    assert not await skills.delete_owned(bob, skill.id)
    assert await skills.delete_owned(alice, skill.id)
    assert await skills.list_for_user(alice) == []
    assert await skills.get_content(alice, "notes") is None
    # Deleting a skill deletes its files.
    async with db_pool.connection() as conn:
        cur = await conn.execute(
            "SELECT count(*) FROM user_skill_files WHERE skill_id = %s", (skill.id,)
        )
        assert await cur.fetchone() == (0,)


async def test_a_skills_name_is_checked_by_the_table(
    db_pool: AsyncConnectionPool[AsyncConnection],
    users: tuple[uuid.UUID, uuid.UUID],
) -> None:
    with pytest.raises(CheckViolation):
        await SkillRepository(db_pool).save(users[0], "Not A Name", "d", "i", {})
