import asyncio

from rag.domain.errors import DocumentNotFoundError
from rag.domain.models import Chunk
from rag.domain.ports import QueryExpanderPort, RerankerPort, VectorStorePort


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStorePort,
        expander: QueryExpanderPort,
        reranker: RerankerPort,
        top_k: int,
    ):
        self._vector_store = vector_store
        self._expander = expander
        self._reranker = reranker
        self._top_k = top_k  # passages a search returns

    async def search(self, query: str) -> list[tuple[Chunk, float]]:
        """Searches with `query` and each of its phrasings, merges the passages found,
        reranks them against `query` and keeps the best `top_k`.
        """
        queries = [query, *await self._expander.expand(query)]

        found = await asyncio.gather(
            *(
                self._vector_store.asimilarity_search_with_score(q, k=self._top_k)
                for q in queries
            )
        )
        candidates = _merge(found)
        ranked = await self._reranker.rerank(query, candidates)
        return ranked[: self._top_k]

    async def get_document(self, source_id: str) -> Chunk:
        document = await self._vector_store.aget_document(source_id)
        if document is None:
            raise DocumentNotFoundError(source_id)
        return document

    async def ping(self) -> None:
        await self._vector_store.aping()


def _merge(found: list[list[tuple[Chunk, float]]]) -> list[tuple[Chunk, float]]:
    """Each passage once, with its best score, the best first. Every search scores
    with the same function, so their scores compare. Ties keep the first query's order.
    """
    best: dict[str, tuple[Chunk, float]] = {}
    for chunk, score in (result for results in found for result in results):
        if chunk.text not in best or score > best[chunk.text][1]:
            best[chunk.text] = (chunk, score)
    return sorted(best.values(), key=lambda result: -result[1])
