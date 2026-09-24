from collections.abc import AsyncIterator, Mapping
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from rag.domain.events import (
    SourcesReady,
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)

# Only the agent node's tokens are the user-facing answer — guardrail's and verify's
# own LLM calls (classification, not an answer) run through this same graph and would
# otherwise leak into the text stream too, since astream_events captures every chat
# model call in the run, not just this one.
_USER_FACING_NODE = "agent"


async def stream_events(
    graph: CompiledStateGraph, messages: list[BaseMessage], config: RunnableConfig
) -> AsyncIterator[StreamEvent]:
    async for raw_event in graph.astream_events(
        {"messages": messages}, config=config, version="v2"
    ):
        event = _parse_event(raw_event)
        if event is not None:
            yield event

    final_state = await graph.aget_state(config)
    sources = sorted(set(final_state.values.get("sources", [])))
    if sources:
        yield SourcesReady(sources=sources)


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
            name=raw_event["name"],
            output=_tool_output_text(raw_event["data"].get("output", "")),
        )

    return None


def _tool_output_text(output: Any) -> str:
    """A tool that needs to update graph state (e.g. search_kb writing `sources`)
    returns a Command instead of a plain string — astream_events reports that
    Command object itself as the output, so pull the real content back out of the
    ToolMessage it carries rather than stringifying the Command.
    """
    if isinstance(output, Command) and isinstance(output.update, dict):
        messages = output.update.get("messages") or []
        if messages:
            return str(messages[0].content)
    return str(output)
