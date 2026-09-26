import uuid
from dataclasses import dataclass, field
from datetime import datetime


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
