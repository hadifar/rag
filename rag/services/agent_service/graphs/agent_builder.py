from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain.agents.middleware.todo import WRITE_TODOS_SYSTEM_PROMPT
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from rag.domain.models import (
    GroundednessMiddleware,
    Middleware,
    OffTopicMiddleware,
    PreferenceMiddleware,
    TodolistMiddleware,
    Tool,
    ToolAgentSpec,
)
from rag.services.agent_service.middleware.groundness import GroundednessGuard
from rag.services.agent_service.middleware.preferences import (
    PREFERENCE_TOOL_NAMES,
    ChatContext,
    PreferencesMiddleware,
)
from rag.services.agent_service.middleware.topical import Classify, TopicalGuard
from rag.services.agent_service.prompts import FALLBACK_MESSAGE


def _fallback_message(_exc: Exception) -> str:
    return FALLBACK_MESSAGE


def _to_langchain_tool(tool: Tool) -> BaseTool:
    """The model reads the result's content; its references ride along as the
    ToolMessage's artifact, where the turn's references are collected from.
    """

    async def run(query: str) -> tuple[str, list[str] | None]:
        result = await tool.run(query)
        return result.content, result.references

    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=tool.description,
        response_format="content_and_artifact",
    )


def _to_langchain_tools(
    tools: list[Tool], reserved: frozenset[str] = frozenset()
) -> list[BaseTool]:
    """Raises ValueError if two tools share a name, or one takes a `reserved` name (a
    middleware's tool), which LangChain would otherwise only trip over once the agent
    runs.
    """
    names = [tool.name for tool in tools] + sorted(reserved)
    if duplicates := sorted({name for name in names if names.count(name) > 1}):
        raise ValueError(f"tool names must be unique: {', '.join(duplicates)}")

    return [_to_langchain_tool(tool) for tool in tools]


def _to_langchain_middleware(
    middleware: Middleware, classify: Classify, user_tools: frozenset[str]
) -> AgentMiddleware[Any, Any]:
    """`user_tools` act on the user, not the product: the model keeps them off-topic,
    and their results aren't what an answer is checked against.
    """
    match middleware:
        case OffTopicMiddleware():
            return TopicalGuard(classify, kept_tools=user_tools)
        case GroundednessMiddleware(max_revisions=max_revisions):
            return GroundednessGuard(
                classify, max_revisions=max_revisions, unverified_tools=user_tools
            )
        case PreferenceMiddleware():
            return PreferencesMiddleware()
        case TodolistMiddleware(instructions=instructions):
            # The instructions come with the tool, so the model is never told to plan
            # with a tool it doesn't have.
            return TodoListMiddleware(
                system_prompt=f"{WRITE_TODOS_SYSTEM_PROMPT}\n\n{instructions}"
            )


def build_tool_agent(
    llm: BaseChatModel,
    spec: ToolAgentSpec,
    classify: Classify,
    checkpointer: BaseCheckpointSaver,
    store: BaseStore,
    retry_attempts: int,
) -> CompiledStateGraph:

    remember_preferences = any(
        isinstance(m, PreferenceMiddleware) for m in spec.middleware
    )

    user_tools = PREFERENCE_TOOL_NAMES if remember_preferences else frozenset()
    tools = _to_langchain_tools(spec.tools, reserved=user_tools)

    middleware = [
        _to_langchain_middleware(m, classify, user_tools) for m in spec.middleware
    ]
    middleware.append(
        ModelRetryMiddleware(
            max_retries=retry_attempts - 1, on_failure=_fallback_message
        )
    )
    # TODO: why we have context_schema!?
    return create_agent(
        llm,
        tools,
        system_prompt=spec.system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
        store=store,
        context_schema=ChatContext,
    )
