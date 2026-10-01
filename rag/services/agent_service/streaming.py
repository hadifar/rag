from collections.abc import Mapping
from typing import Any

from langchain_core.messages import AIMessageChunk, ToolMessage

from rag.domain.models import ReasoningDelta, StreamEvent, TextDelta, ToolCall

# Only create_agent's model node produces the user-facing answer. The guards' own LLM
# calls (classification, not an answer) run in their middleware nodes of this same
# graph and would otherwise leak into the text stream too, since astream_events
# captures every chat model call in the run, not just this one.
_USER_FACING_NODE = "model"


def parse_event(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """The user-facing events a raw graph event stands for; none if it isn't one."""
    kind = raw_event["event"]

    if kind == "on_chat_model_stream":
        if raw_event.get("metadata", {}).get("langgraph_node") != _USER_FACING_NODE:
            return []
        return _chunk_events(raw_event["data"]["chunk"])

    if kind == "on_tool_start":
        return [
            ToolCall(
                name=raw_event["name"],
                status="pending",
                query=raw_event["data"].get("input", {}).get("query", ""),
            )
        ]

    if kind == "on_tool_end":
        return [
            ToolCall(
                name=raw_event["name"],
                status="done",
                output=_tool_output_text(raw_event["data"].get("output", "")),
            )
        ]

    return []


def _chunk_events(chunk: AIMessageChunk) -> list[StreamEvent]:
    """A chunk's text and reasoning, read from its provider-neutral content blocks: a
    plain string for Chat Completions, a list of blocks for the Responses API.
    """
    events: list[StreamEvent] = []
    for block in chunk.content_blocks:
        if block["type"] == "text" and block["text"]:
            events.append(TextDelta(text=block["text"]))
        elif block["type"] == "reasoning" and "reasoning" in block:
            # Each summary part opens with an empty block; a paragraph break keeps one
            # part's last sentence from running into the next part's heading.
            events.append(ReasoningDelta(text=block["reasoning"] or "\n\n"))
    return events


def _tool_output_text(output: Any) -> str:
    """ToolNode reports a ToolMessage as the tool's output; the text is its content."""
    if isinstance(output, ToolMessage):
        return str(output.content)
    return str(output)
