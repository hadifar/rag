from typing import Protocol

from rag.domain.models import Chunk


class EmbeddingsPort(Protocol):
    async def aembed_query(self, text: str) -> list[float]: ...
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...


class VectorStorePort(Protocol):
    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Chunk, float]]: ...
    async def aget_document(self, source_id: str) -> Chunk | None: ...
    async def aping(self) -> None:
        """Raises if the store can't serve queries; must be cheap (readiness probe)."""
        ...


class RerankerPort(Protocol):
    async def rerank(
        self, query: str, candidates: list[tuple[Chunk, float]]
    ) -> list[tuple[Chunk, float]]:
        """The `candidates` relevant to `query`, the best first, each with its score;
        possibly none. Raises if it can't judge them.
        """
        ...


class SearchPort(Protocol):
    """Finds knowledge-base passages for a query: the best first, with their scores."""

    async def search(self, query: str) -> list[tuple[Chunk, float]]: ...
