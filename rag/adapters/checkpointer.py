from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings

_DictRowPool = AsyncConnectionPool[AsyncConnection[DictRow]]


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver]:
    """Opens the checkpointer's connection pool for the caller's scope and tears it down
    on exit.
    """
    async with _DictRowPool(
        settings.CHECKPOINTER.DATABASE_URL.get_secret_value(),
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        check=_DictRowPool.check_connection,
        open=False,
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        yield checkpointer
