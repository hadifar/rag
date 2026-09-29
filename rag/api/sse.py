from collections.abc import Callable
from enum import StrEnum
from typing import Any

from fastapi.sse import ServerSentEvent

from rag.domain.events import (
    SourcesReady,
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)


class SseEventType(StrEnum):
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    SOURCES = "sources"


_ENCODERS: dict[type, Callable[[Any], tuple[SseEventType, Any]]] = {
    TextDelta: lambda e: (SseEventType.TEXT, {"text": e.text}),
    ToolCallStart: lambda e: (
        SseEventType.TOOL_START,
        {"name": e.name, "query": e.query},
    ),
    ToolCallResult: lambda e: (
        SseEventType.TOOL_RESULT,
        {"name": e.name, "output": e.output},
    ),
    SourcesReady: lambda e: (SseEventType.SOURCES, {"sources": e.sources}),
}


def to_sse(event: StreamEvent) -> ServerSentEvent:
    event_type, data = _ENCODERS[type(event)](event)
    return ServerSentEvent(event=event_type, data=data)
