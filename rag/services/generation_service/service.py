from collections.abc import AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag.services.generation_service.graph import build_graph
from rag.services.generation_service.streaming import StreamEvent, stream_events
from rag.services.generation_service.tools import build_search_tool
from rag.services.ranking_service.service import RankingService


class GenerationService:
    def __init__(
        self,
        llm: BaseChatModel,
        ranking_service: RankingService,
        checkpointer: BaseCheckpointSaver,
    ):
        tools = [build_search_tool(ranking_service)]
        self._graph = build_graph(llm, tools, checkpointer)

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        async for event in stream_events(
            self._graph, [HumanMessage(content=message)], config
        ):
            yield event
