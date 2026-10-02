import uuid
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse

from rag.api.deps import (
    AuthenticatedUserDep,
    ConversationServiceDep,
    RagServiceDep,
    get_current_user,
)
from rag.api.schema.agent import StreamEventResponse, to_stream_event
from rag.api.schema.conversation import MessageRequest

router = APIRouter(
    prefix="/api/conversations",
    tags=["rag"],
    dependencies=[Depends(get_current_user)],
)


async def _require_owned_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    """Gate for the streaming route: runs before the response starts, so a missing or
    foreign conversation is a plain 404 rather than an error in an already-200 stream.
    """
    await conversation_service.get_owned(current_user.id, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_class=EventSourceResponse,
    dependencies=[Depends(_require_owned_conversation)],
)
async def send_message(
    conversation_id: uuid.UUID,
    message_request: MessageRequest,
    current_user: AuthenticatedUserDep,
    rag_service: RagServiceDep,
) -> AsyncIterable[StreamEventResponse]:
    """Streams the answer as server-sent events, one `StreamEventResponse` each."""
    async for event in rag_service.stream_chat(
        message_request.message, conversation_id, current_user.id
    ):
        yield to_stream_event(event)
