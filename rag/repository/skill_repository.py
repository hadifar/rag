import uuid
from collections.abc import Mapping

from rag.domain.models import Skill, SkillContent
from rag.repository.base_repository import BaseRepository

_COLUMNS = """
    s.id, s.name, s.description,
    (SELECT count(*) FROM user_skill_files f WHERE f.skill_id = s.id)::int
        AS file_count,
    s.created_at, s.updated_at
"""


class SkillRepository(BaseRepository[Skill]):
    row_type = Skill

    async def save(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str,
        instructions: str,
        files: Mapping[str, str],
    ) -> Skill:
        # One transaction: a skill is never seen with its old files or half its new ones.
        async with self._pool.connection() as conn, conn.transaction():
            cur = await conn.execute(
                """
                INSERT INTO user_skills (user_id, name, description, instructions)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, name) DO UPDATE SET
                    description = EXCLUDED.description,
                    instructions = EXCLUDED.instructions,
                    updated_at = now()
                RETURNING id
                """,
                (user_id, name, description, instructions),
            )
            row = await cur.fetchone()
            assert row is not None  # an INSERT ... RETURNING always returns it
            skill_id = row[0]
            await conn.execute(
                "DELETE FROM user_skill_files WHERE skill_id = %s", (skill_id,)
            )
            await conn.execute(
                """
                INSERT INTO user_skill_files (skill_id, path, content)
                SELECT %s, path, content FROM unnest(%s::text[], %s::text[])
                    AS f (path, content)
                """,
                (skill_id, list(files), list(files.values())),
            )
        skill = await self._fetch_one(
            f"SELECT {_COLUMNS} FROM user_skills s WHERE s.id = %s", (skill_id,)
        )
        assert skill is not None  # just saved; only its owner can delete it
        return skill

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]:
        return await self._fetch_all(
            f"SELECT {_COLUMNS} FROM user_skills s WHERE s.user_id = %s ORDER BY s.name",
            (user_id,),
        )

    async def content(self, user_id: uuid.UUID, name: str) -> SkillContent | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT s.instructions, array(
                    SELECT f.path FROM user_skill_files f
                    WHERE f.skill_id = s.id ORDER BY f.path
                )
                FROM user_skills s WHERE s.user_id = %s AND s.name = %s
                """,
                (user_id, name),
            )
            row = await cur.fetchone()
        return SkillContent(instructions=row[0], files=tuple(row[1])) if row else None

    async def file(self, user_id: uuid.UUID, name: str, path: str) -> str | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT f.content
                FROM user_skill_files f JOIN user_skills s ON s.id = f.skill_id
                WHERE s.user_id = %s AND s.name = %s AND f.path = %s
                """,
                (user_id, name, path),
            )
            row = await cur.fetchone()
        return row[0] if row else None

    async def delete_owned(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        deleted = await self._execute(
            "DELETE FROM user_skills WHERE id = %s AND user_id = %s",
            (skill_id, user_id),
        )
        return deleted > 0
