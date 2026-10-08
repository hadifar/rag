import logging
from collections.abc import AsyncIterator, Mapping
from typing import Any

from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

from rag.domain.models import (
    AgentMemory,
    AnswerChecked,
    ReasoningDelta,
    StreamEvent,
    TextDelta,
    TodosUpdated,
    ToolCall,
    TurnFailed,
)
from rag.services.agent_service.memory import remember
from rag.services.agent_service.prompts import TURN_FAILED_MESSAGE

logger = logging.getLogger(__name__)

# The custom events RagAgent's guard nodes dispatch, which the stream turns into
# user-facing events (see _guard_events).
# check_answer: the answer's check starting, then its verdict.
ANSWER_CHECK = "answer_check"
# check_input: a blocked message, with the refusal sent instead of an answer.
INPUT_BLOCKED = "input_blocked"

# Only RagAgent's model and decline nodes produce the user-facing answer. The guards' own LLM
# calls (verdicts, not an answer) run in their own nodes of this same
# graph and would otherwise leak into the text stream too, since astream_events
# captures every chat model call in the run, not just this one.
_USER_FACING_NODES = frozenset({"model", "decline"})

# LangChain's planning tool, which RagAgent uses as is. Its call is the plan, not a
# search, so it's sent as the plan itself; it returns a Command whose state update holds
# the new todos.
_PLANNING_TOOL = "write_todos"


class AgentTurn:
    """One turn: iterate it for its events, as the user is to see them (see
    `AnswerGate`), then what its tools handed the user. Once they end, `memory` holds
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
            async for event in self._gated_events():
                yield event
            self.memory, artifacts = remember(self._messages, self._question)
            if artifacts is not None:
                yield artifacts
        except Exception:
            logger.exception("chat turn failed")
            self.memory = None
            yield TurnFailed(message=TURN_FAILED_MESSAGE)

    async def _gated_events(self) -> AsyncIterator[StreamEvent]:
        gate = AnswerGate()
        async for raw_event in self._run:
            # The run's own end (it has no parent) carries the final state.
            if raw_event["event"] == "on_chain_end" and not raw_event["parent_ids"]:
                self._messages = raw_event["data"]["output"]["messages"]
            for released in [r for e in parse_event(raw_event) for r in gate.feed(e)]:
                yield released
        for released in gate.flush():
            yield released


def parse_event(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """The user-facing events a raw graph event stands for; none if it isn't one."""
    kind = raw_event["event"]

    if kind == "on_chat_model_stream":
        if (
            raw_event.get("metadata", {}).get("langgraph_node")
            not in _USER_FACING_NODES
        ):
            return []
        return _chunk_events(raw_event["data"]["chunk"])

    if kind in ("on_tool_start", "on_tool_end"):
        return _tool_events(raw_event)

    if kind == "on_custom_event":
        return _guard_events(raw_event)

    return []


class AnswerGate:
    """Holds back answer text the answer guard may still reject, so the user never
    sees an answer that is then taken back. Text streams live until a tool runs in the
    turn: with nothing retrieved there is nothing to check it against. After that, each
    model call's text is held until it is clear what it was: released before the next
    tool call (the model was still working), after a passing verdict, or at the end of
    the turn (an answer that wasn't checked); dropped on a failing verdict, as the guard
    then has the model revise it. Reasoning and every other event pass straight through.
    """

    def __init__(self):
        self._checkable = False
        self._held: list[TextDelta] = []

    def feed(self, event: StreamEvent) -> list[StreamEvent]:
        """What to send for `event` now: none while it's held, else it and any text
        it releases, in the order they were produced.
        """
        match event:
            case TextDelta() if self._checkable:
                self._held.append(event)
                return []
            case ToolCall() | TodosUpdated():
                self._checkable = True
                return [*self.flush(), event]
            case AnswerChecked(status="done", grounded=False):
                self._held.clear()
                return [event]
            case AnswerChecked(status="done"):
                return [event, *self.flush()]
            case _:
                return [event]

    def flush(self) -> list[StreamEvent]:
        """The held text, released; call it once the turn ends."""
        held, self._held = self._held, []
        return list(held)


def _guard_events(raw_event: Mapping[str, Any]) -> list[StreamEvent]:
    """What the guards dispatched: the answer's check starting, then its verdict; or
    the refusal for a blocked message, sent as the answer's text. Other custom events
    aren't streamed.
    """
    name, data = raw_event["name"], raw_event["data"]
    if name == ANSWER_CHECK:
        return [AnswerChecked(status=data["status"], grounded=data.get("grounded"))]
    if name == INPUT_BLOCKED:
        return [TextDelta(text=data["message"])]
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
