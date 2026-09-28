import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from rag.domain.models import Conversation


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, conversation: Conversation) -> "ConversationResponse":
        return cls(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


class ConversationPageResponse(BaseModel):
    items: list[ConversationResponse]
    next_cursor: str | None


class HistoryMessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    sources: list[str] | None
