from collections.abc import AsyncIterator, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag.domain.events import StreamEvent
from rag.services.generation_service.graph import build_graph
from rag.services.generation_service.streaming import stream_events
from rag.services.generation_service.tools import build_search_tool
from rag.services.retrieval_service.service import RetrievalService


def _no_trace(name: str | None = None) -> RunnableConfig:
    return {}


class GenerationService:
    def __init__(
        self,
        llm: BaseChatModel,
        ranking_service: RetrievalService,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig] = _no_trace,
    ):
        tools = [build_search_tool(ranking_service)]
        self._graph = build_graph(llm, tools, checkpointer)
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
