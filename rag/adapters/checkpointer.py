from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from rag.config import Settings


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver]:
    """Opens the checkpointer connection for the caller's scope and tears it down on
    exit — mirrors rag.adapters.pinecone_client.open_vector_store.
    """
    if settings.CHECKPOINTER_BACKEND == "memory":
        yield InMemorySaver()
        return

    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is required when CHECKPOINTER_BACKEND=postgres")

    async with AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URL
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
