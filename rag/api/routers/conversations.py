import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from rag.api.deps import (
    AuthenticatedUserDep,
    ConversationServiceDep,
    get_current_user,
)
from rag.api.schema.conversations import (
    ConversationPageResponse,
    ConversationResponse,
    HistoryMessageResponse,
    MessageRequest,
)

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@router.post("")
async def create_conversation(
    current_user: AuthenticatedUserDep, conversation_service: ConversationServiceDep
) -> ConversationResponse:
    """The caller's empty conversation: a new one, or the one they already have."""
    conversation = await conversation_service.create(current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.get("")
async def list_conversations(
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: str | None = None,
) -> ConversationPageResponse:
    page = await conversation_service.list_for_user(current_user.id, limit, cursor)
    return ConversationPageResponse.model_validate(page)


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> list[HistoryMessageResponse]:
    history = await conversation_service.history(current_user.id, conversation_id)
    return [HistoryMessageResponse.model_validate(m) for m in history]


@router.post("/{conversation_id}/touch", status_code=204)
async def touch_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    """Marks the conversation as just used, so it sorts first in the list; the client
    calls it as it sends a message.
    """
    await conversation_service.touch(current_user.id, conversation_id)


@router.post("/{conversation_id}/title")
async def generate_title(
    conversation_id: uuid.UUID,
    message_request: MessageRequest,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    """Names the conversation from its first message (an LLM-written title, or one cut
    from the message if that fails); the client calls it as it sends that message,
    without waiting for the answer.
    """
    conversation = await conversation_service.generate_title(
        current_user.id, conversation_id, message_request.message
    )
    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    await conversation_service.delete(current_user.id, conversation_id)
