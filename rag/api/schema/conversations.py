import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

MAX_MESSAGE_LENGTH = 8192  # characters in one user message

# Conversation list paging
MAX_PAGE_SIZE = 100
PageLimit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
DEFAULT_PAGE_LIMIT = 30


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None  # Null until the conversation's first turn
    created_at: datetime
    updated_at: datetime


class ConversationPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ConversationResponse]
    next_cursor: str | None


class HistoryMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: Literal["user", "assistant"]
    text: str
    sources: list[str] | None


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
