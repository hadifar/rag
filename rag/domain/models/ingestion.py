import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from rag.domain.models.retrieval import Chunk


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict[str, str])


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
