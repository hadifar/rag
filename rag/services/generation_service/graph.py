import operator
from functools import partial
from typing import Annotated, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from rag.services.generation_service.guards.groundness import (
    REVISION_INSTRUCTION,
    is_grounded,
)
from rag.services.generation_service.guards.topical import (
    OFF_TOPIC_INSTRUCTION,
    is_relevant,
)

MAX_VERIFY_ATTEMPTS = 1
LLM_RETRY_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "You are a support assistant for AtlasFlow. Use the search_kb tool to find relevant "
    "documentation before answering. Only answer based on retrieved content, and say you "
    "don't know if the knowledge base doesn't cover it. Cite the source file(s) you used."
)

FALLBACK_MESSAGE = "I'm having trouble reaching the language model right now. Please try again shortly."


class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    sources: NotRequired[Annotated[list[str], operator.add]]
    relevant: NotRequired[bool]
    grounded: NotRequired[bool]
    verify_attempts: NotRequired[int]


def _fallback_response(_input: object) -> AIMessage:
    return AIMessage(content=FALLBACK_MESSAGE)


def _with_resilience(llm: Runnable) -> Runnable:
    """Retries transient failures, then falls back to a fixed apology message rather
    than propagating the error into the graph run (would 500 the chat request).
    """
    return llm.with_retry(stop_after_attempt=LLM_RETRY_ATTEMPTS).with_fallbacks(
        [RunnableLambda(_fallback_response)]
    )


async def _guardrail(llm: Runnable, state: GraphState) -> dict:

    if await is_relevant(llm, state["messages"]):
        return {"relevant": True}

    return {
        "relevant": False,
        "messages": [SystemMessage(content=OFF_TOPIC_INSTRUCTION)],
    }


async def _call_model(llm_with_tools: Runnable, state: GraphState) -> dict:
    messages = state["messages"]
    if not messages or messages[0].type != "system":
        messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def _verify(llm: Runnable, state: GraphState) -> dict:
    attempts = state.get("verify_attempts", 0)
    grounded = await is_grounded(llm, state["messages"])

    # Fail open past the retry cap: force an end rather than loop forever or make the
    # user wait on the LLM indefinitely re-answering the same question.
    if grounded or attempts >= MAX_VERIFY_ATTEMPTS:
        return {"grounded": True}

    return {
        "grounded": False,
        "verify_attempts": attempts + 1,
        "messages": [HumanMessage(content=REVISION_INSTRUCTION)],
    }


def _route_after_verify(state: GraphState) -> str:
    return END if state.get("grounded") else "agent"


def build_graph(
    llm: BaseChatModel, tools: list[BaseTool], checkpointer: BaseCheckpointSaver
) -> CompiledStateGraph:
    resilient_llm = _with_resilience(llm)
    llm_with_tools = _with_resilience(llm.bind_tools(tools))

    graph = StateGraph(GraphState)
    graph.add_node("guardrail", partial(_guardrail, resilient_llm))
    graph.add_node("agent", partial(_call_model, llm_with_tools))
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("verify", partial(_verify, resilient_llm))

    graph.set_entry_point("guardrail")
    graph.add_edge("guardrail", "agent")
    graph.add_conditional_edges(
        "agent", tools_condition, {"tools": "tools", END: "verify"}
    )
    graph.add_edge("tools", "agent")
    graph.add_conditional_edges(
        "verify", _route_after_verify, {"agent": "agent", END: END}
    )
    return graph.compile(checkpointer=checkpointer)
