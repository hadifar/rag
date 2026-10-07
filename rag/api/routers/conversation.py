import uuid

from fastapi import APIRouter, Depends

from rag.api.deps import (
    AuthenticatedUserDep,
    ConversationServiceDep,
    get_current_user,
)
from rag.api.schema.conversation import (
    DEFAULT_PAGE_LIMIT,
    ConversationPageResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    HistoryMessageResponse,
    MessageRequest,
    PageLimit,
    to_history_message,
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
    limit: PageLimit = DEFAULT_PAGE_LIMIT,
    cursor: str | None = None,
) -> ConversationPageResponse:
    page = await conversation_service.list_for_user(current_user.id, limit, cursor)
    return ConversationPageResponse.model_validate(page)


@router.get("/pinned")
async def list_pinned_conversations(
    current_user: AuthenticatedUserDep, conversation_service: ConversationServiceDep
) -> list[ConversationResponse]:
    """The caller's pinned conversations, last pinned first; `GET ""` lists the rest."""
    conversations = await conversation_service.list_pinned(current_user.id)
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: uuid.UUID,
    update_request: ConversationUpdateRequest,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    """Renames, pins or unpins it."""
    conversation = await conversation_service.update(
        current_user.id,
        conversation_id,
        title=update_request.title,
        pinned=update_request.pinned,
    )
    return ConversationResponse.model_validate(conversation)


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> list[HistoryMessageResponse]:
    history = await conversation_service.history(current_user.id, conversation_id)
    return [to_history_message(m) for m in history]


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
