import uuid
from collections.abc import AsyncIterator, Callable

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from rag.domain.models import ReferencesReady, StreamEvent
from rag.services.agent_service.preferences import ChatContext
from rag.services.agent_service.streaming import parse_event
from rag.services.agent_service.turn import turn_references

# TODO: error hanlding -> Something went wrong: Unexpected end of JSON input


class Agent:
    """A chat agent on any message-state graph: streams each turn's events, then what its
    tools cited. The graph saves the turn's messages through its checkpointer; the agent
    service reads them back (`AgentService.get_history`).
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        trace_config: Callable[[str | None], RunnableConfig],
    ):
        self._graph = graph
        self._trace_config = trace_config

    def _config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}, **self._trace_config("chat")}

    async def stream(
        self, message: str, thread_id: str, user_id: uuid.UUID
    ) -> AsyncIterator[StreamEvent]:
        config = self._config(thread_id)

        async for raw_event in self._graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            context=ChatContext(user_id=user_id),
            version="v2",
        ):
            event = parse_event(raw_event)
            if event is not None:
                yield event

        final_state = await self._graph.aget_state(config)
        references = turn_references(final_state.values.get("messages", []))
        if references is not None:
            yield ReferencesReady(references=references)
