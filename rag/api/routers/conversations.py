import uuid
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from rag.api.deps import ConversationServiceDep, CurrentUserDep, get_current_user
from rag.api.schema.conversations import (
    ConversationPageResponse,
    ConversationResponse,
    HistoryMessageResponse,
    MessageRequest,
)
from rag.api.sse import to_sse

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@router.post("")
async def create_conversation(
    current_user: CurrentUserDep, conversation_service: ConversationServiceDep
) -> ConversationResponse:
    """The caller's empty conversation: a new one, or the one they already have."""
    conversation = await conversation_service.create(current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.get("")
async def list_conversations(
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: str | None = None,
) -> ConversationPageResponse:
    page = await conversation_service.list_for_user(current_user.id, limit, cursor)
    return ConversationPageResponse.model_validate(page)


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> list[HistoryMessageResponse]:
    history = await conversation_service.history(current_user.id, conversation_id)
    return [HistoryMessageResponse.model_validate(m) for m in history]


async def _require_owned_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
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
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> AsyncIterable[ServerSentEvent]:
    """Streams the answer as server-sent events; see rag/api/sse.py for the events."""
    async for event in conversation_service.chat(
        current_user.id, conversation_id, message_request.message
    ):
        yield to_sse(event)


@router.post("/{conversation_id}/title")
async def generate_title(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    """Renames the conversation with an LLM-written title for its first exchange; the
    client calls it once the first answer has streamed.
    """
    conversation = await conversation_service.generate_title(
        current_user.id, conversation_id
    )
    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    await conversation_service.delete(current_user.id, conversation_id)
