from collections.abc import AsyncIterator, Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.domain.constants import LLM_RETRY_ATTEMPTS, MAX_REVISIONS
from rag.domain.events import SourcesReady, StreamEvent
from rag.domain.prompts import FALLBACK_MESSAGE, SYSTEM_PROMPT
from rag.services.agent_service.guards.groundness import GroundednessGuard
from rag.services.agent_service.guards.topical import Classify, TopicalGuard
from rag.services.agent_service.streaming import parse_event
from rag.services.agent_service.turn import turn_sources


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def build_graph(
    llm: BaseChatModel,
    classify: Classify,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    middleware: list[AgentMiddleware[Any, Any]] = [
        TopicalGuard(classify),
        GroundednessGuard(classify, max_revisions=MAX_REVISIONS),
        TodoListMiddleware(),
        ModelRetryMiddleware(
            max_retries=LLM_RETRY_ATTEMPTS - 1, on_failure=_fallback_message
        ),
    ]
    return create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
    )


class RagAgent:
    """The chat agent grounded in the knowledge base: its answers are guarded (off-topic
    and groundedness checks), and each turn ends with the sources it searched. It saves
    the turn's messages through the checkpointer; reading them back is the conversation
    repository's job.
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        trace_config: Callable[[str | None], RunnableConfig],
    ):
        self._graph = graph
        self._trace_config = trace_config

    def get_config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}, **self._trace_config("chat")}

    async def stream(self, message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        config = self.get_config(thread_id)

        async for raw_event in self._graph.astream_events(
            {"messages": [HumanMessage(content=message)]}, config=config, version="v2"
        ):
            event = parse_event(raw_event)
            if event is not None:
                yield event

        final_state = await self._graph.aget_state(config)
        sources = turn_sources(final_state.values.get("messages", []))
        if sources is not None:
            yield SourcesReady(sources=sources)
