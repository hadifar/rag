from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    TodoListMiddleware,
)
from langchain.agents.middleware.todo import WRITE_TODOS_SYSTEM_PROMPT
from langchain.tools import ToolRuntime
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import create_model

from rag.domain.models import (
    GroundednessMiddleware,
    Middleware,
    OffTopicMiddleware,
    RunContext,
    TodolistMiddleware,
    Tool,
    ToolAgentSpec,
)
from rag.services.agent_service.middleware.capabilities import CapabilityInstructions
from rag.services.agent_service.middleware.groundness import GroundednessGuard
from rag.services.agent_service.middleware.judge import Judge
from rag.services.agent_service.middleware.topical import TopicalGuard


def _to_langchain_tool(tool: Tool) -> BaseTool:
    """The model reads the result's content; its references ride along as the
    ToolMessage's artifact, where the turn's references are collected from. The turn's
    RunContext is injected by LangChain, so the model never sees it as an argument.
    """
    fields: dict[str, Any] = {tool.parameter: (str, ...)}
    args_schema = create_model(f"{tool.name}_args", **fields)

    async def run(
        runtime: ToolRuntime[RunContext], **args: str
    ) -> tuple[str, list[str] | None]:
        result = await tool.run(args[tool.parameter], runtime.context)
        return result.content, result.references

    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=tool.description,
        args_schema=args_schema,
        response_format="content_and_artifact",
    )


def _to_langchain_tools(tools: list[Tool]) -> list[BaseTool]:
    """Raises ValueError if two tools share a name, which LangChain would otherwise only
    trip over once the agent runs.
    """
    names = [tool.name for tool in tools]
    if duplicates := sorted({name for name in names if names.count(name) > 1}):
        raise ValueError(f"tool names must be unique: {', '.join(duplicates)}")

    return [_to_langchain_tool(tool) for tool in tools]


def _to_langchain_middleware(
    middleware: Middleware, judge: Judge, user_tools: frozenset[str]
) -> AgentMiddleware[Any, Any]:
    """`user_tools` act on the user, not the product: the model keeps them off-topic,
    and their results aren't what an answer is checked against.
    """
    match middleware:
        case OffTopicMiddleware():
            return TopicalGuard(judge, kept_tools=user_tools)
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


def build_tool_agent(
    llm: BaseChatModel,
    spec: ToolAgentSpec,
    judge: Judge,
    checkpointer: BaseCheckpointSaver,
    retry_attempts: int,
) -> CompiledStateGraph:
    all_tools = [
        *spec.tools,
        *(tool for capability in spec.capabilities for tool in capability.tools),
    ]
    tools = _to_langchain_tools(all_tools)
    user_tools = frozenset(t.name for t in all_tools if t.kind == "user")

    middleware = [
        _to_langchain_middleware(m, judge, user_tools) for m in spec.middleware
    ]
    if any(capability.instructions for capability in spec.capabilities):
        middleware.append(CapabilityInstructions(spec.capabilities))
    # Once its retries run out, the model's error ends the turn (see Agent.stream),
    # rather than an apology standing in for the answer.
    middleware.append(
        ModelRetryMiddleware(max_retries=retry_attempts - 1, on_failure="error")
    )
    # context_schema: each turn is run with its RunContext, which tools and middleware
    # read from their runtime (e.g. whose preferences to apply).
    return create_agent(
        llm,
        tools,
        system_prompt=spec.system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=RunContext,
    )
