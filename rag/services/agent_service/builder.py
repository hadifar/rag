from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from rag.domain.models import RunContext, ToolAgentSpec
from rag.services.agent_service.middleware.factory import build_middleware
from rag.services.agent_service.middleware.judge import Judge
from rag.services.agent_service.tools import to_langchain_tools


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
    tools = to_langchain_tools(all_tools)
    user_tools = frozenset(t.name for t in all_tools if t.kind == "user")

    middleware = build_middleware(spec, judge, user_tools)
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
