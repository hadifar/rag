import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, RootModel

from rag.api.schema.agent import StreamEventResponse, to_stream_event
from rag.domain.models import AssistantMessage, HistoryMessage, UserMessage

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
    match message:
        case UserMessage(text=text):
            return HistoryMessageResponse(UserMessageResponse(text=text))
        case AssistantMessage(events=events):
            return HistoryMessageResponse(
                AssistantMessageResponse(events=[to_stream_event(e) for e in events])
            )


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
