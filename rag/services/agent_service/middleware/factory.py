from typing import Any

from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware
from langchain.agents.middleware.todo import WRITE_TODOS_SYSTEM_PROMPT

from rag.domain.models import (
    GroundednessMiddleware,
    Middleware,
    OffTopicMiddleware,
    TodolistMiddleware,
    ToolAgentSpec,
)
from rag.services.agent_service.middleware.capabilities import CapabilityInstructions
from rag.services.agent_service.middleware.groundedness import GroundednessGuard
from rag.services.agent_service.middleware.judge import Judge
from rag.services.agent_service.middleware.off_topic import OffTopicGuard


def _to_langchain_middleware(
    middleware: Middleware, judge: Judge, user_tools: frozenset[str]
) -> AgentMiddleware[Any, Any]:
    match middleware:
        case OffTopicMiddleware():
            return OffTopicGuard(judge, kept_tools=user_tools)
        case GroundednessMiddleware(max_revisions=max_revisions):
            return GroundednessGuard(
                judge, max_revisions=max_revisions, unverified_tools=user_tools
            )
        case TodolistMiddleware(instructions=instructions):
            # The instructions come with the tool, so the model is never told to plan
            # with a tool it doesn't have.
            return TodoListMiddleware(
                system_prompt=f"{WRITE_TODOS_SYSTEM_PROMPT}\n\n{instructions}"
            )


def build_middleware(
    spec: ToolAgentSpec, judge: Judge, user_tools: frozenset[str]
) -> list[AgentMiddleware[Any, Any]]:
    """The LangChain middleware for `spec`'s middleware, in order, then its
    capabilities' instructions. `user_tools` act on the user, not the product: the
    model keeps them off-topic, and their results aren't what an answer is checked
    against.
    """
    middleware = [
        _to_langchain_middleware(m, judge, user_tools) for m in spec.middleware
    ]
    if any(capability.instructions for capability in spec.capabilities):
        middleware.append(CapabilityInstructions(spec.capabilities))
    return middleware
