from typing import Any, ClassVar, LiteralString

from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool


class BaseRepository[T]:
    """Base for repositories whose rows map onto one domain dataclass, `row_type`."""

    row_type: ClassVar[type[Any]]

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]):
        self._pool = pool

    async def _fetch_one(self, query: LiteralString, params: Any = ()) -> T | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(self.row_type)) as cur,
        ):
            await cur.execute(query, params)
            return await cur.fetchone()

    async def _fetch_all(self, query: LiteralString, params: Any = ()) -> list[T]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(self.row_type)) as cur,
        ):
            await cur.execute(query, params)
            return await cur.fetchall()

    async def _execute(self, query: LiteralString, params: Any = ()) -> int:
        """Runs a statement that returns no rows; returns how many rows it affected."""
        async with self._pool.connection() as conn:
            cur = await conn.execute(query, params)
            return cur.rowcount
