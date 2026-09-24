import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from rag.api.deps import ContainerDep
from rag.api.schema import ChatRequest
from rag.domain.events import StreamEvent, TextDelta, ToolCallResult, ToolCallStart


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
            return _format("text", text)
        case ToolCallStart(name=name, args=args):
            return _format("tool_start", json.dumps({"name": name, "args": args}))
        case ToolCallResult(name=name, output=output):
            return _format("tool_result", json.dumps({"name": name, "output": output}))


def _format(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"
