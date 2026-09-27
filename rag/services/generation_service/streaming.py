from collections.abc import AsyncIterator, Mapping
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from rag.domain.events import (
    SourcesReady,
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)
from rag.services.generation_service.turn import turn_sources

# Only create_agent's model node produces the user-facing answer. The guards' own LLM
# calls (classification, not an answer) run in their middleware nodes of this same
# graph and would otherwise leak into the text stream too, since astream_events
# captures every chat model call in the run, not just this one.
_USER_FACING_NODE = "model"


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
    sources = turn_sources(final_state.values.get("messages", []))
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
            name=raw_event["name"],
            query=raw_event["data"].get("input", {}).get("query", ""),
        )

    if kind == "on_tool_end":
        return ToolCallResult(
            name=raw_event["name"],
            output=_tool_output_text(raw_event["data"].get("output", "")),
        )

    return None


def _tool_output_text(output: Any) -> str:
    """ToolNode reports a ToolMessage as the tool's output; the text is its content."""
    if isinstance(output, ToolMessage):
        return str(output.content)
    return str(output)
