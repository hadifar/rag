import uuid
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse

from rag.api.deps import (
    AttachmentsToSendDep,
    AuthenticatedUserDep,
    ChatServiceDep,
    ConversationServiceDep,
    get_current_user,
)
from rag.api.schema.chat import StreamEventResponse, to_stream_event
from rag.api.schema.conversation import ChatMessageRequest

router = APIRouter(
    prefix="/api/chat", tags=["chat"], dependencies=[Depends(get_current_user)]
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
    "/{conversation_id}",
    response_class=EventSourceResponse,
    dependencies=[Depends(_require_owned_conversation)],
)
async def send_message(
    conversation_id: uuid.UUID,
    message_request: ChatMessageRequest,
    attachments: AttachmentsToSendDep,
    current_user: AuthenticatedUserDep,
    chat_service: ChatServiceDep,
) -> AsyncIterable[StreamEventResponse]:
    """Streams the answer as server-sent events, one `StreamEventResponse` each. The
    message's attachments are uploaded to the conversation first
    (`POST /api/conversations/{conversation_id}/attachments`).
    """
    async for event in chat_service.send_message(
        current_user.id, conversation_id, message_request.message, attachments
    ):
        yield to_stream_event(event)
