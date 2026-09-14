"""Normalizes LangGraph's astream_events into one small vocabulary that both the
FastAPI SSE endpoint and the Gradio UI consume directly — one translation point,
two renderers.
"""

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable, RunnableConfig


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallStart:
    name: str
    args: dict


@dataclass
class ToolCallResult:
    name: str
    output: str


StreamEvent = TextDelta | ToolCallStart | ToolCallResult

# Only the agent node's tokens are the user-facing answer — guardrail's and verify's
# own LLM calls (classification, not an answer) run through this same graph and would
# otherwise leak into the text stream too, since astream_events captures every chat
# model call in the run, not just this one.
_USER_FACING_NODE = "agent"


async def stream_events(
    graph: Runnable, messages: list[BaseMessage], config: RunnableConfig
) -> AsyncIterator[StreamEvent]:
    async for raw_event in graph.astream_events(
        {"messages": messages}, config=config, version="v2"
    ):
        event = _parse_event(raw_event)
        if event is not None:
            yield event


def _parse_event(raw_event: Mapping[str, Any]) -> StreamEvent | None:
    kind = raw_event["event"]
    if kind == "on_chat_model_stream":
        if raw_event.get("metadata", {}).get("langgraph_node") != _USER_FACING_NODE:
            return None
        chunk = raw_event["data"]["chunk"]
        return TextDelta(text=chunk.content) if chunk.content else None
    if kind == "on_tool_start":
        return ToolCallStart(
            name=raw_event["name"], args=raw_event["data"].get("input", {})
        )
    if kind == "on_tool_end":
        return ToolCallResult(
            name=raw_event["name"], output=str(raw_event["data"].get("output", ""))
        )
    return None
