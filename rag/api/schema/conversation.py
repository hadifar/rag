import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, RootModel

from rag.api.schema.agent import StreamEventResponse
from rag.api.schema.text import UserText
from rag.domain.models import HistoryMessage

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


class UserMessageResponse(BaseModel):
    role: Literal["user"] = "user"
    text: str


class AssistantMessageResponse(BaseModel):
    """A past answer as the events its stream sent, in order; replayed like the live stream."""

    role: Literal["assistant"] = "assistant"
    events: list[StreamEventResponse]


class HistoryMessageResponse(
    RootModel[
        Annotated[
            UserMessageResponse | AssistantMessageResponse,
            Field(discriminator="role"),
        ]
    ]
):
    """One message of a saved conversation, told apart by `role`."""


def to_history_message(message: HistoryMessage) -> HistoryMessageResponse:
    """The API model for a domain message: both carry the same fields and `role` tag."""
    return HistoryMessageResponse.model_validate(asdict(message))


class MessageRequest(BaseModel):
    message: UserText = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
