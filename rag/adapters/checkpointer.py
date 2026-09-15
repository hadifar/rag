from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from rag.config import Settings


def build_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    if settings.CHECKPOINTER_BACKEND == "memory":
        return InMemorySaver()
    raise ValueError(
        f"Unsupported checkpointer backend: {settings.CHECKPOINTER_BACKEND}"
    )
