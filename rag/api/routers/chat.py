import json
from enum import StrEnum

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from rag.api.deps import ContainerDep
from rag.api.schema import ChatRequest
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


def build_chat_router() -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/stream")
    async def stream(
        chat_request: ChatRequest, container: ContainerDep
    ) -> StreamingResponse:
        generation_service = container.generation_service

        async def event_stream():
            async for event in generation_service.stream_chat(
                chat_request.message, chat_request.thread_id
            ):
                yield _to_sse(event)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router


def _to_sse(event: StreamEvent) -> str:
    match event:
        case TextDelta(text=text):
            return _format(SseEventType.TEXT, text)
        case ToolCallStart(name=name, query=query):
            return _format(
                SseEventType.TOOL_START, json.dumps({"name": name, "query": query})
            )
        case ToolCallResult(name=name, output=output):
            return _format(
                SseEventType.TOOL_RESULT, json.dumps({"name": name, "output": output})
            )
        case SourcesReady(sources=sources):
            return _format(SseEventType.SOURCES, json.dumps({"names": sources}))


def _format(event: SseEventType, data: str) -> str:
    return f"event: {event.value}\ndata: {data}\n\n"
