import logging
from collections.abc import AsyncIterator, Mapping
from typing import Any

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

from rag.domain.models import (
    AgentMemory,
    ReasoningDelta,
    StreamEvent,
    TextDelta,
    TodosUpdated,
    ToolCall,
    TurnFailed,
)
from rag.services.agent_service.memory import remember
from rag.services.agent_service.prompts import TURN_FAILED_MESSAGE
from rag.services.agent_service.tools import SKILL_FILE_TOOL, SKILL_TOOL

logger = logging.getLogger(__name__)

# The custom event check_input dispatches (with `input_blocked`) for a blocked message,
# with the refusal sent instead of an answer.
_INPUT_BLOCKED = "input_blocked"

# Only RagAgent's answer and decline nodes write the user-facing answer; research's
# reasoning is shown too, but its text (only "Done.") isn't. The input guard's own LLM
# calls (verdicts, not an answer) run in this same graph and would otherwise leak into
# the stream too, since astream_events captures every chat model call in the run.
_ANSWER_NODES = frozenset({"answer", "decline"})
_REASONING_NODES = _ANSWER_NODES | {"research"}

# LangChain's planning tool, which RagAgent uses as is. Its call is the plan, not a
# search, so it's sent as the plan itself; it returns a Command whose state update holds
# the new todos.
_PLANNING_TOOL = "write_todos"

# Their output is a skill's text, for the model to follow, not for the user to read.
_SKILL_TOOLS = frozenset({SKILL_TOOL, SKILL_FILE_TOOL})


class AgentTurn:
    """One turn: iterate it for its events, as the user is to see them, then what its
    tools handed the user. Once they end, `memory` holds
    the turn's messages, from the question on; it stays None for a turn to forget: a
    blocked question, a failed tool or model call (whose unanswered tool call the
    model's API would reject in every later turn), or a stream its caller stopped
    reading.
    """

    def __init__(self, run: AsyncIterator[Any], question: HumanMessage):
        self._run = run
        self._question = question
        self._messages: list[BaseMessage] = []  # the run's, once it ends
        self.memory: AgentMemory | None = None

    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        """If a tool or the model fails, the turn ends with `TurnFailed` instead."""
        try:
            async for event in self._events():
                yield event
            self.memory, artifacts = remember(self._messages, self._question)
            if artifacts is not None:
                yield artifacts
        except Exception:
            logger.exception("chat turn failed")
            self.memory = None
            yield TurnFailed(message=TURN_FAILED_MESSAGE)

    async def _events(self) -> AsyncIterator[StreamEvent]:
        async for raw_event in self._run:
            # The run's own end (it has no parent) carries the final state.
            if raw_event["event"] == "on_chain_end" and not raw_event["parent_ids"]:
                self._messages = raw_event["data"]["output"]["messages"]
            for event in parse_event(raw_event):
                yield event


def parse_event(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """The user-facing events a raw graph event stands for; none if it isn't one."""
    kind = raw_event["event"]

    if kind == "on_chat_model_stream":
        node = raw_event.get("metadata", {}).get("langgraph_node")
        if node not in _REASONING_NODES:
            return []
        return _chunk_events(raw_event["data"]["chunk"], text=node in _ANSWER_NODES)

    if kind in ("on_tool_start", "on_tool_end"):
        return _tool_events(raw_event)

    if kind == "on_custom_event":
        return _guard_events(raw_event)

    return []


async def input_blocked(message: str) -> None:
    """Sends `message`, the refusal, as the blocked question's answer."""
    await adispatch_custom_event(_INPUT_BLOCKED, {"message": message})


def _guard_events(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """The refusal for a blocked message, sent as the answer's text. Other custom
    events aren't streamed.
    """
    if raw_event["name"] == _INPUT_BLOCKED:
        return [TextDelta(text=raw_event["data"]["message"])]
    return []


def _tool_events(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """A tool call is shown `pending`, then `done` with its output, each with a label
    for the user; a skill tool's output is left out. The planning tool is shown only
    once it's done, as the plan its state update holds.
    """
    started = raw_event["event"] == "on_tool_start"
    name = raw_event["name"]
    data = raw_event["data"]
    args = data.get("input") or {}

    if name == _PLANNING_TOOL:
        return [] if started else [TodosUpdated(todos=data["output"].update["todos"])]

    if started:
        return [
            ToolCall(
                name=name,
                status="pending",
                label=_tool_label(name, args, done=False),
                query=args.get("query", ""),
            )
        ]
    return [
        ToolCall(
            name=name,
            status="done",
            label=_tool_label(name, args, done=True),
            output=None
            if name in _SKILL_TOOLS
            else _tool_output_text(data.get("output", "")),
        )
    ]


def _tool_label(name: str, args: Mapping[str, Any], *, done: bool) -> str:
    """What the chat shows for a tool call, from its arguments; an unknown tool's
    name as is.
    """
    if name == "search_kb":
        return f"{'Searched' if done else 'Searching'}: {args.get('query', '')}"
    if name == SKILL_TOOL:
        return f"{'Loaded' if done else 'Loading'} skill: {args.get('name', '')}"
    if name == SKILL_FILE_TOOL:
        verb = "Read" if done else "Reading"
        return f"{verb} {args.get('path', '')} from {args.get('skill', '')}"
    return name


def _chunk_events(chunk: AIMessageChunk, *, text: bool) -> list[StreamEvent]:
    """A chunk's reasoning, and its text if `text`, read from its provider-neutral
    content blocks: a plain string for Chat Completions, a list of blocks for the
    Responses API.
    """
    events: list[StreamEvent] = []
    for block in chunk.content_blocks:
        if block["type"] == "text" and block["text"] and text:
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
