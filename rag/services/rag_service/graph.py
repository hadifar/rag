from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.services.rag_service.guards.groundness import GroundednessGuard
from rag.services.rag_service.guards.topical import TopicalGuard
from rag.services.rag_service.resilience import (
    FALLBACK_MESSAGE,
    LLM_RETRY_ATTEMPTS,
    with_resilience,
)

SYSTEM_PROMPT = (
    "You are a support assistant for AtlasFlow. Use the search_kb tool to find relevant "
    "documentation before answering. Only answer based on retrieved content, and say you "
    "don't know if the knowledge base doesn't cover it."
)

MAX_REVISIONS = 1


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def build_graph(
    llm: BaseChatModel, tools: list[BaseTool], checkpointer: BaseCheckpointSaver
) -> CompiledStateGraph:

    classifier = with_resilience(llm)

    middleware: list[AgentMiddleware[Any, Any]] = [
        TopicalGuard(classifier),
        GroundednessGuard(classifier, max_revisions=MAX_REVISIONS),
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
