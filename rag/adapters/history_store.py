from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag.domain.models import HistoryMessage
from rag.services.rag_service.turn import to_history


class CheckpointHistoryStore:
    """The messages the chat agent saves per thread, read back as the user saw them."""

    def __init__(self, checkpointer: BaseCheckpointSaver[str]):
        self._checkpointer = checkpointer

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        checkpoint = await self._checkpointer.aget(
            {"configurable": {"thread_id": thread_id}}
        )
        messages: list[BaseMessage] = (
            checkpoint["channel_values"].get("messages", []) if checkpoint else []
        )
        return to_history(messages)

    async def delete_history(self, thread_id: str) -> None:
        await self._checkpointer.adelete_thread(thread_id)

    async def list_thread_ids(self) -> set[str]:
        return {
            thread_id
            async for checkpoint in self._checkpointer.alist(None)
            if (thread_id := checkpoint.config.get("configurable", {}).get("thread_id"))
        }
