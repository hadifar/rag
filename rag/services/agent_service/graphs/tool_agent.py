from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain.agents.middleware.todo import WRITE_TODOS_SYSTEM_PROMPT
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.domain.agents import Check, GroundednessCheck, OffTopicCheck, ToolAgentSpec
from rag.domain.constants import LLM_RETRY_ATTEMPTS
from rag.services.agent_service.guards.groundness import GroundednessGuard
from rag.services.agent_service.guards.topical import Classify, TopicalGuard
from rag.services.agent_service.prompts import FALLBACK_MESSAGE


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def _guard(check: Check, classify: Classify) -> AgentMiddleware[Any, Any]:
    match check:
        case OffTopicCheck():
            return TopicalGuard(classify)
        case GroundednessCheck(max_revisions=max_revisions):
            return GroundednessGuard(classify, max_revisions=max_revisions)


def build_tool_agent(
    llm: BaseChatModel,
    spec: ToolAgentSpec,
    classify: Classify,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    # The checks come first: the outermost middleware, so an off-topic turn's "no
    # tools" also covers planning's write_todos.
    middleware: list[AgentMiddleware[Any, Any]] = [
        *(_guard(check, classify) for check in spec.checks)
    ]
    if spec.planning is not None:
        # The instructions come with the tool, so the model is never told to plan
        # with a tool it doesn't have.
        instructions = f"{WRITE_TODOS_SYSTEM_PROMPT}\n\n{spec.planning.instructions}"
        middleware.append(TodoListMiddleware(system_prompt=instructions))
    middleware.append(
        ModelRetryMiddleware(
            max_retries=LLM_RETRY_ATTEMPTS - 1, on_failure=_fallback_message
        )
    )
    return create_agent(
        llm,
        cast(list[BaseTool], spec.tools),  # only the agent service builds them
        system_prompt=spec.system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )
