from collections.abc import AsyncIterator

from rag.domain.events import StreamEvent
from rag.domain.ports import AgentServicePort, SearchPort


class RagService:
    """A chat turn grounded in the knowledge base: the agent service's guarded chat
    agent, searching `retrieval_service`.
    """

    def __init__(self, retrieval_service: SearchPort, agent_service: AgentServicePort):
        search_tool = agent_service.create_tool(retrieval_service)
        self._agent = agent_service.create_rag_agent([search_tool])

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._agent.stream(message, thread_id):
            yield event
