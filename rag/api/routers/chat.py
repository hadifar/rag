import json
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from rag.api.deps import ConversationServiceDep, CurrentUserDep
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


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
async def stream(
    chat_request: ChatRequest,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> StreamingResponse:
    # Resolved before the response starts, so an unknown or foreign conversation is a
    # plain 404 rather than an error in the middle of an already-200 stream.
    turn = await conversation_service.start_turn(
        current_user.id, chat_request.conversation_id, chat_request.message
    )

    async def event_stream():
        async for event in conversation_service.stream_turn(turn, chat_request.message):
            yield _to_sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Every payload is single-line JSON: json.dumps escapes "\n", which would otherwise end
# the SSE event early and drop the rest of e.g. a markdown token.
_ENCODERS: dict[type, Callable[[Any], tuple[SseEventType, str]]] = {
    ConversationReady: lambda e: (
        SseEventType.CONVERSATION,
        ConversationResponse.from_domain(e.conversation).model_dump_json(),
    ),
    TextDelta: lambda e: (SseEventType.TEXT, json.dumps({"text": e.text})),
    ToolCallStart: lambda e: (
        SseEventType.TOOL_START,
        json.dumps({"name": e.name, "query": e.query}),
    ),
    ToolCallResult: lambda e: (
        SseEventType.TOOL_RESULT,
        json.dumps({"name": e.name, "output": e.output}),
    ),
    SourcesReady: lambda e: (SseEventType.SOURCES, json.dumps({"sources": e.sources})),
    ConversationTitled: lambda e: (
        SseEventType.TITLE,
        json.dumps({"id": e.conversation_id, "title": e.title}),
    ),
}


def _to_sse(event: StreamEvent) -> str:
    event_type, data = _ENCODERS[type(event)](event)
    return f"event: {event_type.value}\ndata: {data}\n\n"
