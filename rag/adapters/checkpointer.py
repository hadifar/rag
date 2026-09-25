from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from rag.config import MemoryCheckpointer, PostgresCheckpointer, Settings


@asynccontextmanager
async def _open_memory(
    config: MemoryCheckpointer,
) -> AsyncGenerator[BaseCheckpointSaver]:
    yield InMemorySaver()


@asynccontextmanager
async def _open_postgres(
    config: PostgresCheckpointer,
) -> AsyncGenerator[BaseCheckpointSaver]:
    async with AsyncPostgresSaver.from_conn_string(
        config.DATABASE_URL.get_secret_value()
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver]:
    """Opens the checkpointer connection for the caller's scope and tears it down on exit"""
    match settings.CHECKPOINTER:
        case MemoryCheckpointer() as config:
            async with _open_memory(config) as checkpointer:
                yield checkpointer
        case PostgresCheckpointer() as config:
            async with _open_postgres(config) as checkpointer:
                yield checkpointer
