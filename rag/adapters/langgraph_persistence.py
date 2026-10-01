from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.base import BaseStore
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings

_DictRowPool = AsyncConnectionPool[AsyncConnection[DictRow]]

# LangGraph's tables live in their own Postgres schema, apart from ours in `public`: they
# belong to the library (its setup() creates and migrates them), never to Alembic.
LANGGRAPH_SCHEMA = "langgraph"


@dataclass(frozen=True)
class LangGraphPersistence:
    checkpointer: BaseCheckpointSaver[str]  # each thread's messages
    store: BaseStore  # what outlives a thread (e.g. a user's preferences)


@asynccontextmanager
async def open_langgraph(settings: Settings) -> AsyncGenerator[LangGraphPersistence]:
    """Opens the checkpointer and the store on one connection pool of their own for the
    caller's scope and tears it down on exit. Same database as `open_db_pool`, but a
    separate pool: both need dict rows, autocommit, no prepared statements and their own
    schema on every connection.
    """
    async with _DictRowPool(
        settings.DATABASE_URL.get_secret_value(),
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "options": f"-c search_path={LANGGRAPH_SCHEMA}",
        },
        check=_DictRowPool.check_connection,
        open=False,
    ) as pool:
        # Created here as well as by migration 0008, so the app can start (and run its
        # migrations from inside the container) on a database that hasn't had them yet.
        async with pool.connection() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {LANGGRAPH_SCHEMA}")
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        store = AsyncPostgresStore(pool)
        await store.setup()
        yield LangGraphPersistence(checkpointer, store)
