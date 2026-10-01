from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

from rag.domain.models import (
    ReasoningDelta,
    ReferencesReady,
    StreamEvent,
    TextDelta,
    ToolCall,
)

# The message stream's events: each is one SSE `data:` line of JSON, told apart by `type`.


class TextEvent(BaseModel):
    """A piece of the answer, in order."""

    type: Literal["text"] = "text"
    text: str


class ReasoningEvent(BaseModel):
    """A piece of the model's reasoning summary, in order. Live only: not in history."""

    type: Literal["reasoning"] = "reasoning"
    text: str


class ToolEvent(BaseModel):
    """A knowledge-base search: `pending` with its query, then `done` with its output."""

    type: Literal["tool"] = "tool"
    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None


class ReferencesEvent(BaseModel):
    """The turn's deduplicated references, once it's done. Only sent if the turn searched."""

    type: Literal["references"] = "references"
    references: list[str]


class StreamEventResponse(
    RootModel[
        Annotated[
            TextEvent | ReasoningEvent | ToolEvent | ReferencesEvent,
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
) -> TextEvent | ReasoningEvent | ToolEvent | ReferencesEvent:
    match event:
        case TextDelta(text=text):
            return TextEvent(text=text)
        case ReasoningDelta(text=text):
            return ReasoningEvent(text=text)
        case ToolCall(name=name, status=status, query=query, output=output):
            return ToolEvent(name=name, status=status, query=query, output=output)
        case ReferencesReady(references=references):
            return ReferencesEvent(references=references)
