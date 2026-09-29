from collections.abc import AsyncIterator, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag.domain.events import StreamEvent
from rag.domain.models import HistoryMessage
from rag.domain.ports import SearchPort
from rag.services.generation_service.graph import build_graph
from rag.services.generation_service.streaming import stream_events
from rag.services.generation_service.title import generate_title
from rag.services.generation_service.tools import build_search_tool
from rag.services.generation_service.turn import to_history


def _no_trace(name: str | None = None) -> RunnableConfig:
    return {}


class GenerationService:
    def __init__(
        self,
        llm: BaseChatModel,
        knowledge_base: SearchPort,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig] = _no_trace,
    ):
        tools = [build_search_tool(knowledge_base)]
        self._llm = llm
        self._graph = build_graph(llm, tools, checkpointer)
        self._checkpointer = checkpointer
        self._trace_config = trace_config

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id},
            **self._trace_config("chat"),
        }
        async for event in stream_events(
            self._graph, [HumanMessage(content=message)], config
        ):
            yield event

    async def generate_title(self, question: str, answer: str) -> str | None:
        return await generate_title(self._llm, question, answer)

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        state = await self._graph.aget_state({"configurable": {"thread_id": thread_id}})
        return to_history(state.values.get("messages", []))

    async def delete_history(self, thread_id: str) -> None:
        await self._checkpointer.adelete_thread(thread_id)

    async def list_thread_ids(self) -> set[str]:
        return {
            thread_id
            async for checkpoint in self._checkpointer.alist(None)
            if (thread_id := checkpoint.config.get("configurable", {}).get("thread_id"))
        }
