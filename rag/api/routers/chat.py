from collections.abc import AsyncIterable, Callable
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from rag.api.deps import ConversationServiceDep, TurnDep, get_current_user
from rag.api.schema.chat import ChatRequest
from rag.api.schema.conversations import ConversationResponse
from rag.domain.events import (
    ConversationReady,
    ConversationTitled,
    SourcesReady,
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)


class SseEventType(StrEnum):
    CONVERSATION = "conversation"
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    SOURCES = "sources"
    TITLE = "title"


router = APIRouter(
    prefix="/api/chat", tags=["chat"], dependencies=[Depends(get_current_user)]
)


@router.post("/stream", response_class=EventSourceResponse)
async def stream(
    chat_request: ChatRequest,
    turn: TurnDep,
    conversation_service: ConversationServiceDep,
) -> AsyncIterable[ServerSentEvent]:
    async for event in conversation_service.stream_turn(turn, chat_request.message):
        yield _to_sse(event)


_ENCODERS: dict[type, Callable[[Any], tuple[SseEventType, Any]]] = {
    ConversationReady: lambda e: (
        SseEventType.CONVERSATION,
        ConversationResponse.model_validate(e.conversation),
    ),
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
    ConversationTitled: lambda e: (
        SseEventType.TITLE,
        {"id": e.conversation_id, "title": e.title},
    ),
}


def _to_sse(event: StreamEvent) -> ServerSentEvent:
    event_type, data = _ENCODERS[type(event)](event)
    return ServerSentEvent(event=event_type, data=data)
