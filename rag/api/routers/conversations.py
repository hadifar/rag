import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from rag.api.deps import ConversationServiceDep, CurrentUserDep, get_current_user
from rag.api.schema.conversations import (
    ConversationPageResponse,
    HistoryMessageResponse,
)

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


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


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    await conversation_service.delete(current_user.id, conversation_id)
