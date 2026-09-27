"""Contracts every service depends on instead of a concrete SDK."""

import uuid
from collections.abc import AsyncIterator, Iterable
from datetime import datetime
from typing import Protocol

from langchain_core.documents import Document

from rag.domain.events import StreamEvent
from rag.domain.models import Conversation, HistoryMessage, RawDocument, User


class VectorStorePort(Protocol):
    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Document, float]]: ...
    async def aadd_documents(
        self, documents: list[Document], *, ids: list[str]
    ) -> list[str]: ...
    async def aget_document(self, source_id: str) -> Document | None: ...
    async def aping(self) -> None:
        """Raises if the store can't serve queries; must be cheap (readiness probe)."""
        ...


class DocumentLoaderPort(Protocol):
    """Sync by design: ingestion is a batch CLI operation, not a shared-event-loop hot path."""

    def load(self) -> Iterable[RawDocument]: ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...


class UserRepositoryPort(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def create(self, email: str, hashed_password: str) -> User: ...


class ConversationRepositoryPort(Protocol):
    async def create(
        self, user_id: uuid.UUID, title: str, conversation_id: uuid.UUID | None = None
    ) -> Conversation:
        """`conversation_id` is the client's id for it; None generates one."""
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


class ChatEnginePort(Protocol):
    """Runs chat turns and owns their message history, keyed by thread id."""

    def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]: ...
    async def get_history(self, thread_id: str) -> list[HistoryMessage]: ...
    async def delete_history(self, thread_id: str) -> None: ...
