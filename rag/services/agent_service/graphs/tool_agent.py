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

from rag.domain.constants import LLM_RETRY_ATTEMPTS
from rag.domain.models import (
    Check,
    GroundednessCheck,
    OffTopicCheck,
    Tool,
    ToolAgentSpec,
)
from rag.services.agent_service.guards.groundness import GroundednessGuard
from rag.services.agent_service.guards.topical import Classify, TopicalGuard
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


def _to_langchain_tools(tools: list[Tool]) -> list[BaseTool]:
    """Raises ValueError if two tools share a name, which LangChain would otherwise
    only trip over once the agent runs.
    """
    names = [tool.name for tool in tools]
    if duplicates := sorted({name for name in names if names.count(name) > 1}):
        raise ValueError(f"tool names must be unique: {', '.join(duplicates)}")

    return [_to_langchain_tool(tool) for tool in tools]


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
    tools = _to_langchain_tools(spec.tools)

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
        tools,
        system_prompt=spec.system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )
