import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from rag.api.schema.conversation import HistoryMessageResponse, to_history_message
from rag.domain.models import SharedConversation


class ShareResponse(BaseModel):
    """A conversation's public read-only link: `id` is its token."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str  # The conversation's title when it was shared
    shared_at: datetime  # When the snapshot was taken; later messages aren't shown


class SharedConversationResponse(BaseModel):
    """What anyone with the link sees: the snapshot's title, date and messages."""

    title: str
    shared_at: datetime
    messages: list[HistoryMessageResponse]


def to_shared_conversation(shared: SharedConversation) -> SharedConversationResponse:
    return SharedConversationResponse(
        title=shared.share.title,
        shared_at=shared.share.shared_at,
        messages=[to_history_message(m) for m in shared.history],
    )
