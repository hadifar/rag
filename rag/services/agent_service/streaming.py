from collections.abc import Mapping
from typing import Any

from langchain_core.messages import AIMessageChunk, ToolMessage

from rag.domain.models import (
    AnswerRetracted,
    ReasoningDelta,
    StreamEvent,
    TextDelta,
    TodosUpdated,
    ToolCall,
)

# Only create_agent's model node produces the user-facing answer. The guards' own LLM
# calls (classification, not an answer) run in their middleware nodes of this same
# graph and would otherwise leak into the text stream too, since astream_events
# captures every chat model call in the run, not just this one.
_USER_FACING_NODE = "model"

# TodoListMiddleware's planning tool. Its call is the plan, not a search, so it's sent
# as the plan itself; it returns a Command whose state update holds the new todos.
_PLANNING_TOOL = "write_todos"

# Dispatched (as a custom event) by a guard that rejects the answer it just streamed.
ANSWER_RETRACTED = "answer_retracted"


def parse_event(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """The user-facing events a raw graph event stands for; none if it isn't one."""
    kind = raw_event["event"]

    if kind == "on_chat_model_stream":
        if raw_event.get("metadata", {}).get("langgraph_node") != _USER_FACING_NODE:
            return []
        return _chunk_events(raw_event["data"]["chunk"])

    if kind in ("on_tool_start", "on_tool_end"):
        return _tool_events(raw_event)

    if kind == "on_custom_event" and raw_event["name"] == ANSWER_RETRACTED:
        return [AnswerRetracted()]

    return []


def _tool_events(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """A search is shown `pending` with its query, then `done` with its output; the
    planning tool only once it's done, as the plan its state update holds.
    """
    started = raw_event["event"] == "on_tool_start"
    data = raw_event["data"]

    if raw_event["name"] == _PLANNING_TOOL:
        return [] if started else [TodosUpdated(todos=data["output"].update["todos"])]

    if started:
        return [
            ToolCall(
                name=raw_event["name"],
                status="pending",
                query=data.get("input", {}).get("query", ""),
            )
        ]
    return [
        ToolCall(
            name=raw_event["name"],
            status="done",
            output=_tool_output_text(data.get("output", "")),
        )
    ]


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
