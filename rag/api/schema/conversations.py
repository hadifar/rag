import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from rag.domain.events import (
    SourcesReady,
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None  # Null until the conversation's first turn
    created_at: datetime
    updated_at: datetime


class ConversationPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ConversationResponse]
    next_cursor: str | None


class HistoryMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: Literal["user", "assistant"]
    text: str
    sources: list[str] | None


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8192)


# The message stream's events: each is one SSE `data:` line of JSON, told apart by `type`.


class TextEvent(BaseModel):
    """A piece of the answer, in order."""

    type: Literal["text"] = "text"
    text: str


class ToolEvent(BaseModel):
    """A knowledge-base search: `pending` with its query, then `done` with its output."""

    type: Literal["tool"] = "tool"
    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None


class SourcesEvent(BaseModel):
    """The turn's deduplicated sources, once it's done. Only sent if the turn searched."""

    type: Literal["sources"] = "sources"
    sources: list[str]


StreamEventResponse = Annotated[
    TextEvent | ToolEvent | SourcesEvent, Field(discriminator="type")
]


def to_stream_event(event: StreamEvent) -> StreamEventResponse:
    match event:
        case TextDelta(text=text):
            return TextEvent(text=text)
        case ToolCallStart(name=name, query=query):
            return ToolEvent(name=name, status="pending", query=query)
        case ToolCallResult(name=name, output=output):
            return ToolEvent(name=name, status="done", output=output)
        case SourcesReady(sources=sources):
            return SourcesEvent(sources=sources)
