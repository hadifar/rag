import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict[str, str])


@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict[str, str | int]
    id: str | None = None


@dataclass(frozen=True)
class IndexedDocument:
    source_id: str
    content_hash: str
    chunks: list[Chunk]


@dataclass(frozen=True)
class IngestionReport:
    added: int
    updated: int
    unchanged: int
    removed: int
    chunks: int


IngestionRunStatus = Literal["running", "succeeded", "failed"]


@dataclass(frozen=True)
class IngestionRun:
    """One ingestion of an uploaded archive. The counts are set once it succeeds."""

    id: uuid.UUID
    status: IngestionRunStatus
    archive_name: str
    created_by: uuid.UUID | None
    started_at: datetime
    finished_at: datetime | None = None
    added: int | None = None
    updated: int | None = None
    unchanged: int | None = None
    removed: int | None = None
    chunks: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    created_at: datetime
    # Admins can replace the knowledge base; granted out-of-band (`rag set-admin`).
    is_admin: bool = False


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    user_id: uuid.UUID
    # None only while the conversation is empty: its first message names it.
    title: str | None
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
