"""Contracts every service depends on instead of a concrete SDK."""

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from langchain_core.documents import Document

from rag.domain.events import StreamEvent
from rag.domain.models import (
    Conversation,
    HistoryMessage,
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    RawDocument,
    User,
)


class VectorStorePort(Protocol):
    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Document, float]]: ...
    async def aget_document(self, source_id: str) -> Document | None: ...
    async def aping(self) -> None:
        """Raises if the store can't serve queries; must be cheap (readiness probe)."""
        ...


class DocumentIndexPort(Protocol):
    """The write side of the knowledge base: what's indexed, and replacing it."""

    async def alist_content_hashes(self) -> dict[str, str]:
        """source_id -> content hash, for every indexed document."""
        ...

    async def areplace_documents(
        self, documents: list[IndexedDocument], *, removed: list[str]
    ) -> None:
        """Re-indexes `documents` (embedding their chunks) and drops `removed`, all in
        one transaction.
        """
        ...


class ArchiveStorePort(Protocol):
    """Keeps every uploaded knowledge-base zip, so the index can always be rebuilt."""

    async def asave(self, data: bytes) -> str:
        """Stores `data` under a new name and returns it. Names sort by upload time."""
        ...

    async def aread(self, name: str) -> bytes: ...
    async def alatest(self) -> str | None:
        """The most recently saved archive's name, or None if there are none."""
        ...


class IngestionRunRepositoryPort(Protocol):
    async def create(
        self, archive_name: str, created_by: uuid.UUID | None
    ) -> IngestionRun:
        """Starts a run as `running`; raises IngestionInProgressError if one already is."""
        ...

    async def get(self, run_id: uuid.UUID) -> IngestionRun | None: ...
    async def latest(self) -> IngestionRun | None: ...
    async def running(self) -> IngestionRun | None: ...
    async def finish(self, run_id: uuid.UUID, report: IngestionReport) -> None: ...
    async def fail(self, run_id: uuid.UUID, error: str) -> None: ...
    async def fail_running(self, error: str) -> int:
        """Marks every still-running run failed; returns how many there were."""
        ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...


class UserRepositoryPort(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def create(
        self, email: str, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        """Raises UserAlreadyExistsError if the email is taken."""
        ...

    async def set_admin(self, email: str, is_admin: bool) -> User | None:
        """None if no user has that email."""
        ...


class ConversationRepositoryPort(Protocol):
    async def get_or_create_empty(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty (untitled) conversation, created if they have none, and
        bumped to most recently used. A user has at most one.
        """
        ...

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        """Newest first by (updated_at, id); `before` is exclusive (keyset pagination)."""
        ...

    async def touch(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None: ...
    async def delete(self, conversation_id: uuid.UUID) -> None: ...


class GenerationPort(Protocol):
    """Runs chat turns and owns their message history, keyed by thread id."""

    def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]: ...
    async def generate_title(self, question: str, answer: str) -> str | None:
        """A title for a conversation opening with this exchange, or None if one
        couldn't be generated. Never raises.
        """
        ...

    async def get_history(self, thread_id: str) -> list[HistoryMessage]: ...
    async def delete_history(self, thread_id: str) -> None: ...
