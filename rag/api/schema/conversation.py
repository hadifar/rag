import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal, Self

from fastapi import Query
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    model_validator,
)

from rag.api.schema.chat import StreamEventResponse
from rag.api.schema.common import UserText
from rag.domain.models import ConversationUpdate, Effort, HistoryMessage, ModelName

MAX_MESSAGE_LENGTH = 8192  # characters in one user message
MAX_ATTACHMENTS = 3  # files sent with one message
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
    model: ModelName  # what its turns run on
    effort: Effort


class ConversationPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ConversationResponse]
    next_cursor: str | None


class AttachmentResponse(BaseModel):
    """A file attached to a message; its content is at
    `GET /api/conversations/{conversation_id}/attachments/{id}`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    media_type: str  # what its content was recognized as
    size: int  # bytes


class UserMessageResponse(BaseModel):
    role: Literal["user"] = "user"
    text: str  # empty if the user sent only attachments
    attachments: list[AttachmentResponse] = []


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


class ChatMessageRequest(BaseModel):
    """A message to the chat: its text, its attachments (uploaded to the conversation
    first), or both.
    """

    message: UserText = Field(default="", max_length=MAX_MESSAGE_LENGTH)
    attachment_ids: list[uuid.UUID] = Field(default=[], max_length=MAX_ATTACHMENTS)

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not self.message and not self.attachment_ids:
            raise ValueError("a message needs text or an attachment")
        if len(set(self.attachment_ids)) != len(self.attachment_ids):
            raise ValueError("an attachment is listed twice")
        return self


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
    model: ModelName | None = None
    effort: Effort | None = None

    def to_update(self) -> ConversationUpdate:
        return ConversationUpdate(**self.model_dump())
