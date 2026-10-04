from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

from rag.domain.models import (
    AnswerVerified,
    ReasoningDelta,
    ReferencesReady,
    StreamEvent,
    TextDelta,
    TodosUpdated,
    ToolCall,
)

# The message stream's events: each is one SSE `data:` line of JSON, told apart by `type`.


class TextEvent(BaseModel):
    """A piece of the answer, in order."""

    type: Literal["text"] = "text"
    text: str


class ReasoningEvent(BaseModel):
    """A piece of the model's reasoning summary, in order."""

    type: Literal["reasoning"] = "reasoning"
    text: str


class ToolEvent(BaseModel):
    """A knowledge-base search: `pending` with its query, then `done` with its output."""

    type: Literal["tool"] = "tool"
    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None


class TodoItem(BaseModel):
    content: str
    status: Literal["pending", "in_progress", "completed"]


class TodosEvent(BaseModel):
    """The agent's whole plan, each time it rewrites it."""

    type: Literal["todos"] = "todos"
    todos: list[TodoItem]


class VerificationEvent(BaseModel):
    """The answer checked against what the turn's searches found: `pending` while the
    check runs, then `done` with whether the answer is supported by them.
    """

    type: Literal["verification"] = "verification"
    status: Literal["pending", "done"]
    grounded: bool | None = None


class ReferencesEvent(BaseModel):
    """The turn's deduplicated references, once it's done. Only sent if the turn searched."""

    type: Literal["references"] = "references"
    references: list[str]


class StreamEventResponse(
    RootModel[
        Annotated[
            TextEvent
            | ReasoningEvent
            | ToolEvent
            | TodosEvent
            | VerificationEvent
            | ReferencesEvent,
            Field(discriminator="type"),
        ]
    ]
):
    """One event of the message stream. A named model rather than a bare union, so it's
    in the OpenAPI schema and the frontend's generated types by this name.
    """


def to_stream_event(event: StreamEvent) -> StreamEventResponse:
    return StreamEventResponse(_payload(event))


def _payload(
    event: StreamEvent,
) -> (
    TextEvent
    | ReasoningEvent
    | ToolEvent
    | TodosEvent
    | VerificationEvent
    | ReferencesEvent
):
    match event:
        case TextDelta(text=text):
            return TextEvent(text=text)
        case ReasoningDelta(text=text):
            return ReasoningEvent(text=text)
        case ToolCall() | TodosUpdated():
            return _tool_payload(event)
        case AnswerVerified() | ReferencesReady():
            return _turn_payload(event)


def _turn_payload(
    event: AnswerVerified | ReferencesReady,
) -> VerificationEvent | ReferencesEvent:
    """What becomes of the turn's answer: checked against the searches, or the
    references cited.
    """
    match event:
        case AnswerVerified(status=status, grounded=grounded):
            return VerificationEvent(status=status, grounded=grounded)
        case ReferencesReady(references=references):
            return ReferencesEvent(references=references)


def _tool_payload(event: ToolCall | TodosUpdated) -> ToolEvent | TodosEvent:
    """A tool's call: a search's progress, or the plan the planning tool wrote."""
    match event:
        case ToolCall(name=name, status=status, query=query, output=output):
            return ToolEvent(name=name, status=status, query=query, output=output)
        case TodosUpdated(todos=todos):
            return TodosEvent(
                todos=[TodoItem(content=t.content, status=t.status) for t in todos]
            )
