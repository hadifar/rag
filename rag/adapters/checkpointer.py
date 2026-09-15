from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from rag.config import Settings


def build_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    if settings.CHECKPOINTER_BACKEND == "memory":
        return MemorySaver()
    raise ValueError(
        f"Unsupported checkpointer backend: {settings.CHECKPOINTER_BACKEND}"
    )
