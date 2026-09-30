from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.domain.prompts import (
    FALLBACK_MESSAGE,
    SYSTEM_PROMPT,
)
from rag.services.rag_service.guards.groundness import GroundednessGuard
from rag.services.rag_service.guards.topical import TopicalGuard


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def _fallback_response(_input: object) -> AIMessage:
    return AIMessage(content=FALLBACK_MESSAGE)


def with_resilience(llm: Runnable) -> Runnable:
    return llm.with_retry(stop_after_attempt=3).with_fallbacks(
        [RunnableLambda(_fallback_response)]
    )


def build_graph(
    llm: BaseChatModel, tools: list[BaseTool], checkpointer: BaseCheckpointSaver
) -> CompiledStateGraph:

    classifier = with_resilience(llm)

    middleware: list[AgentMiddleware[Any, Any]] = [
        TopicalGuard(classifier),
        GroundednessGuard(classifier, max_revisions=1),
        TodoListMiddleware(),
        ModelRetryMiddleware(max_retries=2, on_failure=_fallback_message),
    ]
    return create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
    )
