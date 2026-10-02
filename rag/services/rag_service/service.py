import uuid
from collections.abc import AsyncIterator

from rag.domain.models import (
    Capability,
    GroundednessMiddleware,
    OffTopicMiddleware,
    RunContext,
    StreamEvent,
    TodolistMiddleware,
    ToolAgentSpec,
)
from rag.domain.ports import AgentServicePort, SearchPort
from rag.services.rag_service.prompts import PLANNING_INSTRUCTIONS, RAG_SYSTEM_PROMPT
from rag.services.rag_service.tools import search_tool


class RagService:
    """A chat turn grounded in the knowledge base: a tool-calling agent that searches
    `retrieval_service`, declines off-topic questions, and revises answers its searches
    don't support, up to `max_revisions` times per turn. `capabilities` are what other
    features give it (e.g. the user's preferences).
    """

    def __init__(
        self,
        retrieval_service: SearchPort,
        agent_service: AgentServicePort,
        max_revisions: int,
        capabilities: list[Capability],
    ):
        # define agent spec
        agent_spec = ToolAgentSpec(
            system_prompt=RAG_SYSTEM_PROMPT,
            tools=[search_tool(retrieval_service)],
            middleware=[
                OffTopicMiddleware(),
                GroundednessMiddleware(max_revisions),
                TodolistMiddleware(PLANNING_INSTRUCTIONS),
            ],
            capabilities=capabilities,
        )
        # create agent
        self._agent = agent_service.create_agent(agent_spec)

    async def stream_chat(
        self, message: str, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> AsyncIterator[StreamEvent]:
        ctx = RunContext(user_id=user_id, conversation_id=conversation_id)
        async for event in self._agent.stream(message, ctx):
            yield event
