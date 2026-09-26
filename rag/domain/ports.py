"""Contracts every service depends on instead of a concrete SDK."""

import uuid
from collections.abc import Iterable
from typing import Protocol

from langchain_core.documents import Document

from rag.domain.models import RawDocument, User


class VectorStorePort(Protocol):
    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Document, float]]: ...
    async def aadd_documents(
        self, documents: list[Document], *, ids: list[str]
    ) -> list[str]: ...
    async def aget_document(self, source_id: str) -> Document | None: ...


class DocumentLoaderPort(Protocol):
    """Sync by design: ingestion is a batch CLI operation, not a shared-event-loop hot path."""

    def load(self) -> Iterable[RawDocument]: ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...


class UserRepositoryPort(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def create(self, email: str, hashed_password: str) -> User: ...
