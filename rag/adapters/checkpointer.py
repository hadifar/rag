from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from rag.config import Settings


@asynccontextmanager
async def _open_memory(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver]:
    yield InMemorySaver()


@asynccontextmanager
async def _open_postgres(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver]:

    assert settings.DATABASE_URL is not None

    async with AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URL.get_secret_value()
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


_BACKENDS: dict[
    str, Callable[[Settings], AbstractAsyncContextManager[BaseCheckpointSaver]]
] = {
    "memory": _open_memory,
    "postgres": _open_postgres,
}


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver]:
    """Opens the checkpointer connection for the caller's scope and tears it down on exit"""
    async with _BACKENDS[settings.CHECKPOINTER_BACKEND](settings) as checkpointer:
        yield checkpointer
