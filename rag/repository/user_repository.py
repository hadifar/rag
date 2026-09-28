import uuid

from rag.domain.models import User
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, email, hashed_password, created_at, is_admin"


class UserRepository(BaseRepository[User]):
    row_type = User

    async def get_by_email(self, email: str) -> User | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM users WHERE email = %s", (email,)
        )

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM users WHERE id = %s", (user_id,)
        )

    async def create(
        self, email: str, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        user = await self._fetch_one(
            f"""
            INSERT INTO users (id, email, hashed_password, is_admin)
            VALUES (gen_random_uuid(), %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (email, hashed_password, is_admin),
        )
        assert user is not None  # INSERT ... RETURNING always yields a row
        return user

    async def set_admin(self, email: str, is_admin: bool) -> User | None:
        return await self._fetch_one(
            f"UPDATE users SET is_admin = %s WHERE email = %s RETURNING {_COLUMNS}",
            (is_admin, email),
        )
