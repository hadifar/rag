import uuid

from rag.domain.models import Skill
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, name, description, created_at, updated_at"


class SkillRepository(BaseRepository[Skill]):
    row_type = Skill

    async def save(
        self, user_id: uuid.UUID, name: str, description: str, instructions: str
    ) -> Skill:
        skill = await self._fetch_one(
            f"""
            INSERT INTO user_skills (user_id, name, description, instructions)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, name) DO UPDATE SET
                description = EXCLUDED.description,
                instructions = EXCLUDED.instructions,
                updated_at = now()
            RETURNING {_COLUMNS}
            """,
            (user_id, name, description, instructions),
        )
        assert skill is not None  # an INSERT ... RETURNING always returns it
        return skill

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]:
        return await self._fetch_all(
            f"SELECT {_COLUMNS} FROM user_skills WHERE user_id = %s ORDER BY name",
            (user_id,),
        )

    async def get_instructions(self, user_id: uuid.UUID, name: str) -> str | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT instructions FROM user_skills WHERE user_id = %s AND name = %s",
                (user_id, name),
            )
            row = await cur.fetchone()
        return row[0] if row else None

    async def delete_owned(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        deleted = await self._execute(
            "DELETE FROM user_skills WHERE id = %s AND user_id = %s",
            (skill_id, user_id),
        )
        return deleted > 0
