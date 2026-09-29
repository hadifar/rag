from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRetryMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.services.generation_service.guards.groundness import GroundednessGuard
from rag.services.generation_service.guards.topical import TopicalGuard

MAX_REVISIONS = 1
LLM_RETRY_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "You are a support assistant for AtlasFlow. Use the search_kb tool to find relevant "
    "documentation before answering. Only answer based on retrieved content, and say you "
    "don't know if the knowledge base doesn't cover it. Cite the source file(s) you used."
)

FALLBACK_MESSAGE = "I'm having trouble reaching the language model right now. Please try again shortly."


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def _fallback_response(_input: object) -> AIMessage:
    return AIMessage(content=FALLBACK_MESSAGE)


def _with_resilience(llm: Runnable) -> Runnable:
    return llm.with_retry(stop_after_attempt=LLM_RETRY_ATTEMPTS).with_fallbacks(
        [RunnableLambda(_fallback_response)]
    )


def build_graph(
    llm: BaseChatModel, tools: list[BaseTool], checkpointer: BaseCheckpointSaver
) -> CompiledStateGraph:
    classifier = _with_resilience(llm)

    middleware: list[AgentMiddleware[Any, Any]] = [
        TopicalGuard(classifier),
        GroundednessGuard(classifier, max_revisions=MAX_REVISIONS),
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
