import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from rag.api.schema import ChatRequest
from rag.container import ContainerHandle
from rag.services.generation_service.streaming import (
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)


def build_chat_router(handle: ContainerHandle) -> APIRouter:
    router = APIRouter()

    @router.post("/stream")
    async def stream(request: ChatRequest) -> StreamingResponse:
        generation_service = handle.get().generation_service

        async def event_stream():
            async for event in generation_service.stream_chat(
                request.message, request.thread_id
            ):
                yield _to_sse(event)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router


def _to_sse(event: StreamEvent) -> str:
    match event:
        case TextDelta(text=text):
            return _format("text", text)
        case ToolCallStart(name=name, args=args):
            return _format("tool_start", json.dumps({"name": name, "args": args}))
        case ToolCallResult(name=name, output=output):
            return _format("tool_result", json.dumps({"name": name, "output": output}))


def _format(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"
