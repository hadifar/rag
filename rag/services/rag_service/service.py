from collections.abc import AsyncIterator, Callable

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.domain.events import StreamEvent
from rag.domain.ports import ModelPort, SearchPort
from rag.services.rag_service.graph import build_graph
from rag.services.rag_service.streaming import stream_events
from rag.services.rag_service.tools import build_search_tool


def _no_trace(name: str | None = None) -> RunnableConfig:
    return {}


class RagService:
    """A chat turn grounded in the knowledge base: retrieval plus generation. It saves
    the turn's messages through the checkpointer; reading them back is the conversation
    repository's job.
    """

    def __init__(
        self,
        retrieval_service: SearchPort,
        generation_service: ModelPort,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig] = _no_trace,
    ):
        tools = [build_search_tool(retrieval_service)]
        self._graph: CompiledStateGraph = build_graph(
            generation_service.chat_model, tools, checkpointer
        )
        self._trace_config = trace_config

    def get_config(self, thread_id: str):
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id},
            **self._trace_config("chat"),
        }
        return config

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        config: RunnableConfig = self.get_config(thread_id)

        async for event in stream_events(
            self._graph, [HumanMessage(content=message)], config
        ):
            yield event
