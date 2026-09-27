import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from rag.api.deps import ConversationServiceDep, CurrentUserDep
from rag.api.schema.conversations import (
    ConversationPageResponse,
    ConversationResponse,
    HistoryMessageResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: str | None = None,
) -> ConversationPageResponse:
    page = await conversation_service.list_for_user(current_user.id, limit, cursor)
    return ConversationPageResponse(
        items=[ConversationResponse.from_domain(c) for c in page.items],
        next_cursor=page.next_cursor,
    )


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> list[HistoryMessageResponse]:
    history = await conversation_service.history(current_user.id, conversation_id)
    return [
        HistoryMessageResponse(role=m.role, text=m.text, sources=m.sources)
        for m in history
    ]


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    await conversation_service.delete(current_user.id, conversation_id)
