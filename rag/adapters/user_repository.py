import uuid

from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import User


class PostgresUserRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]):
        self._pool = pool

    async def get_by_email(self, email: str) -> User | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                "SELECT id, email, hashed_password, created_at FROM users WHERE email = %s",
                (email,),
            )
            return await cur.fetchone()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                "SELECT id, email, hashed_password, created_at FROM users WHERE id = %s",
                (user_id,),
            )
            return await cur.fetchone()

    async def create(self, email: str, hashed_password: str) -> User:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(User)) as cur,
        ):
            await cur.execute(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (gen_random_uuid(), %s, %s)
                RETURNING id, email, hashed_password, created_at
                """,
                (email, hashed_password),
            )
            row = await cur.fetchone()
            assert row is not None  # INSERT ... RETURNING always yields a row
            return row
