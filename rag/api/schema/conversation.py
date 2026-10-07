import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Query
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, RootModel

from rag.api.schema.chat import StreamEventResponse
from rag.api.schema.common import UserText
from rag.domain.models import HistoryMessage

MAX_MESSAGE_LENGTH = 8192  # characters in one user message
MAX_TITLE_LENGTH = 200  # characters in a title the user writes

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
    pinned_at: datetime | None  # Null while it isn't pinned


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


def _one_line(title: str) -> str:
    return " ".join(title.split())


# A title the user writes: one line, never blank (a null title marks the empty draft).
UserTitle = Annotated[
    UserText,
    AfterValidator(_one_line),
    Field(min_length=1, max_length=MAX_TITLE_LENGTH),
]


class ConversationUpdateRequest(BaseModel):
    """The fields to change; each one left out stays as is."""

    title: UserTitle | None = None
    pinned: bool | None = None
