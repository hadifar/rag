from collections.abc import AsyncIterator, Callable

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from rag.domain.models import ReferencesReady, StreamEvent
from rag.services.agent_service.streaming import parse_event
from rag.services.agent_service.turn import turn_references


class Agent:
    """A chat agent on any message-state graph: streams each turn's events, then what its
    tools cited. The graph saves the turn's messages through its checkpointer; reading
    them back is the conversation repository's job.
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
        references = turn_references(final_state.values.get("messages", []))
        if references is not None:
            yield ReferencesReady(references=references)
