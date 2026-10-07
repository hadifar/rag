import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Attachment:
    """A file the user uploaded to a conversation, to send with a message. It's kept
    with the conversation, and every turn it's sent with lists it.
    """

    id: uuid.UUID
    conversation_id: uuid.UUID
    name: str  # as uploaded, without its directories
    media_type: str  # what its content was recognized as, never what the client said
    size: int  # bytes
    sha256: str  # hex, of its content
    created_at: datetime


@dataclass(frozen=True)
class AttachmentFile:
    """An attachment with its content."""

    attachment: Attachment
    data: bytes
