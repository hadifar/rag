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

    assert (
        settings.DATABASE_URL is not None
    )  # enforced by Settings._require_database_url

    async with AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URL.get_secret_value()
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
