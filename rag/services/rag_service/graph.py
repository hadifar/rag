from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.domain.constants import LLM_RETRY_ATTEMPTS, MAX_REVISIONS
from rag.domain.ports import GenerationPort
from rag.domain.prompts import (
    FALLBACK_MESSAGE,
    SYSTEM_PROMPT,
)
from rag.domain.resilience import or_default
from rag.services.rag_service.guards.groundness import GroundednessGuard
from rag.services.rag_service.guards.topical import TopicalGuard


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def build_graph(
    generation: GenerationPort,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    async def classify(prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            generation.generate(prompt, attempts=LLM_RETRY_ATTEMPTS), FALLBACK_MESSAGE
        )

    middleware: list[AgentMiddleware[Any, Any]] = [
        TopicalGuard(classify),
        GroundednessGuard(classify, max_revisions=MAX_REVISIONS),
        TodoListMiddleware(),
        ModelRetryMiddleware(
            max_retries=LLM_RETRY_ATTEMPTS - 1, on_failure=_fallback_message
        ),
    ]
    return generation.create_agent(
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
    )
