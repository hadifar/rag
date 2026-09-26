from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings


@asynccontextmanager
async def open_db_pool(
    settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    """Opens the auth DB connection pool for the caller's scope and tears it down on exit."""
    pool = AsyncConnectionPool[AsyncConnection](
        settings.AUTH.DATABASE_URL.get_secret_value(), open=False
    )
    async with pool:
        yield pool
