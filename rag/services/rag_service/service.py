from collections.abc import AsyncIterator

from rag.domain.agents import (
    GroundednessCheck,
    OffTopicCheck,
    Planning,
    ToolAgentSpec,
)
from rag.domain.constants import MAX_REVISIONS
from rag.domain.events import StreamEvent
from rag.domain.ports import AgentServicePort, SearchPort
from rag.services.rag_service.prompts import PLANNING_INSTRUCTIONS, RAG_SYSTEM_PROMPT
from rag.services.rag_service.tools import search_tool


class RagService:
    """A chat turn grounded in the knowledge base: a tool-calling agent that searches
    `retrieval_service`, declines off-topic questions, and revises answers its searches
    don't support.
    """

    def __init__(self, retrieval_service: SearchPort, agent_service: AgentServicePort):

        tools = agent_service.create_tools([search_tool(retrieval_service)])

        agent_spec = ToolAgentSpec(
            system_prompt=RAG_SYSTEM_PROMPT,
            tools=tools,
            checks=[OffTopicCheck(), GroundednessCheck(MAX_REVISIONS)],
            planning=Planning(PLANNING_INSTRUCTIONS),
        )

        self._agent = agent_service.create_agent(agent_spec)

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._agent.stream(message, thread_id):
            yield event
