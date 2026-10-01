from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.messages import ToolCall as ToolCallRequest

from rag.domain.models import (
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


def parse_event(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """The user-facing events a raw graph event stands for; none if it isn't one."""
    kind = raw_event["event"]

    if kind == "on_chat_model_stream":
        if raw_event.get("metadata", {}).get("langgraph_node") != _USER_FACING_NODE:
            return []
        return _chunk_events(raw_event["data"]["chunk"])

    if kind in ("on_tool_start", "on_tool_end"):
        return _tool_events(raw_event)

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


def replay(messages: Sequence[BaseMessage]) -> list[StreamEvent]:
    """The events saved messages stand for, in the order they were streamed, so a past
    turn shows as it did live: each reply's reasoning and text, each search `pending`
    then `done`, and each plan the agent wrote.
    """
    events: list[StreamEvent] = []
    for message in messages:
        if isinstance(message, AIMessage):
            events.extend(_reply_events(message))
        elif isinstance(message, ToolMessage) and message.name != _PLANNING_TOOL:
            events.append(
                ToolCall(
                    name=message.name or "",
                    status="done",
                    output=_tool_output_text(message),
                )
            )
    return events


def _reply_events(message: AIMessage) -> list[StreamEvent]:
    events: list[StreamEvent] = []
    for block in message.content_blocks:
        if block["type"] == "text" and block["text"]:
            events.append(TextDelta(text=block["text"]))
        elif block["type"] == "reasoning" and (reasoning := block.get("reasoning")):
            # One block per summary part; live, each part opened with this break.
            events.append(ReasoningDelta(text="\n\n" + reasoning))
    return events + [_call_event(call) for call in message.tool_calls]


def _call_event(call: ToolCallRequest) -> StreamEvent:
    """A search as it started, `pending` with its query; the planning tool's call as
    the plan it wrote.
    """
    if call["name"] == _PLANNING_TOOL:
        return TodosUpdated(todos=call["args"]["todos"])
    return ToolCall(
        name=call["name"], status="pending", query=call["args"].get("query", "")
    )


def _tool_output_text(output: Any) -> str:
    """ToolNode reports a ToolMessage as the tool's output; the text is its content."""
    if isinstance(output, ToolMessage):
        return str(output.content)
    return str(output)
