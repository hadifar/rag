"""Contracts every service depends on instead of a concrete SDK."""

from collections.abc import Iterable
from typing import Protocol

from langchain_core.documents import Document

from rag.domain.models import RawDocument


class VectorStorePort(Protocol):
    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Document, float]]: ...
    async def aadd_documents(
        self, documents: list[Document], *, ids: list[str]
    ) -> list[str]: ...


class DocumentLoaderPort(Protocol):
    """Sync by design: ingestion is a batch CLI operation, not a shared-event-loop hot path."""

    def load(self) -> Iterable[RawDocument]: ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...
