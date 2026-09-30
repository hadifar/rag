from collections.abc import AsyncIterator

from rag.domain.agents import GroundednessCheck, OffTopicCheck, ToolAgentSpec
from rag.domain.constants import MAX_REVISIONS
from rag.domain.events import StreamEvent
from rag.domain.ports import AgentServicePort, SearchPort
from rag.domain.prompts import SYSTEM_PROMPT


class RagService:
    """A chat turn grounded in the knowledge base: a tool-calling agent that searches
    `retrieval_service`, declines off-topic questions, and revises answers its searches
    don't support.
    """

    def __init__(self, retrieval_service: SearchPort, agent_service: AgentServicePort):
        self._agent = agent_service.create_agent(
            ToolAgentSpec(
                system_prompt=SYSTEM_PROMPT,
                tools=[agent_service.create_tool(retrieval_service)],
                checks=[OffTopicCheck(), GroundednessCheck(MAX_REVISIONS)],
                todo_list=True,
            )
        )

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._agent.stream(message, thread_id):
            yield event
