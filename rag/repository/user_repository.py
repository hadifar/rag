import uuid

from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import User

_COLUMNS = "id, email, hashed_password, created_at, is_admin"


class UserRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]):
        self._pool = pool

    async def get_by_email(self, email: str) -> User | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                f"SELECT {_COLUMNS} FROM users WHERE email = %s",
                (email,),
            )
            return await cur.fetchone()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                f"SELECT {_COLUMNS} FROM users WHERE id = %s",
                (user_id,),
            )
            return await cur.fetchone()

    async def create(
        self, email: str, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                f"""
                INSERT INTO users (id, email, hashed_password, is_admin)
                VALUES (gen_random_uuid(), %s, %s, %s)
                RETURNING {_COLUMNS}
                """,
                (email, hashed_password, is_admin),
            )
            row = await cur.fetchone()
            assert row is not None  # INSERT ... RETURNING always yields a row
            return row

    async def set_admin(self, email: str, is_admin: bool) -> User | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                f"UPDATE users SET is_admin = %s WHERE email = %s RETURNING {_COLUMNS}",
                (is_admin, email),
            )
            return await cur.fetchone()
