import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionReport:
    documents: int
    chunks: int


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    created_at: datetime


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConversationPage:
    items: list[Conversation]
    # Opaque; pass back to fetch the next (older) page. None on the last page.
    next_cursor: str | None


@dataclass(frozen=True)
class HistoryMessage:
    role: Literal["user", "assistant"]
    text: str
    # None unless the turn searched the knowledge base; empty if it found nothing.
    sources: list[str] | None = None
