from collections.abc import Sequence

from rag.domain.models import (
    AgentMemory,
    Capability,
    GroundednessMiddleware,
    OffTopicMiddleware,
    RunContext,
    TodolistMiddleware,
    ToolAgentSpec,
)
from rag.domain.ports import ChatTurnPort, LLMServicePort, SearchPort
from rag.services.rag_service.prompts import PLANNING_INSTRUCTIONS, RAG_SYSTEM_PROMPT
from rag.services.rag_service.tools import search_tool


class RagService:
    """The chat agent (a RagServicePort), grounded in the knowledge base: it searches
    `retrieval_service`, declines off-topic questions, and revises answers its searches
    don't support, up to `max_revisions` times per turn. `capabilities` are what other
    features give it (e.g. the user's preferences).
    """

    def __init__(
        self,
        retrieval_service: SearchPort,
        llm_service: LLMServicePort,
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
        self._agent = llm_service.create_agent(agent_spec)

    def stream(
        self, message: str, history: Sequence[AgentMemory], ctx: RunContext
    ) -> ChatTurnPort:
        return self._agent.stream(message, history, ctx)
