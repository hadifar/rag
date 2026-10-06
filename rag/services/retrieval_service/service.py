from rag.domain.errors import DocumentNotFoundError
from rag.domain.models import Chunk
from rag.domain.ports import CachePort, RerankerPort, VectorStorePort
from rag.shared.resilience import or_default
from rag.shared.text_normalizer import normalize_text


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStorePort,
        reranker: RerankerPort,
        candidates: int,
        rerank_candidates: int,
        *,
        cache: CachePort[list[tuple[Chunk, float]]],
    ):
        """`candidates` passages are fetched; the reranker keeps `rerank_candidates` of
        them, or all of them at 0 (no reranking). `cache` keeps each search's result by
        its query.
        """
        self._vector_store = vector_store
        self._reranker = reranker
        self._cache = cache
        self.top_k = rerank_candidates or candidates  # passages a search returns
        self._candidates = max(candidates, self.top_k)  # passages the reranker sees

    async def search(self, query: str) -> list[tuple[Chunk, float]]:
        """Finds the best `candidates` passages for `query`, reranks them against it
        and returns the first `top_k`; a cached result if the query was searched
        before. If reranking fails, the search's own order, which isn't cached.
        """
        # Normalized for the search too, so a cached result is the query's own.
        query = normalize_text(query)
        if cached := await or_default(self._cache.get(query), None):
            return cached

        candidates = await self._vector_store.asimilarity_search_with_score(
            query, k=self._candidates
        )
        reranked = await or_default(self._reranker.rerank(query, candidates), None)
        if reranked is None:
            return candidates[: self.top_k]

        results = reranked[: self.top_k]
        if results:
            await or_default(self._cache.put(query, results), None)
        return results

    async def get_document(self, source_id: str) -> Chunk:
        document = await self._vector_store.aget_document(source_id)
        if document is None:
            raise DocumentNotFoundError(source_id)
        return document

    async def ping(self) -> None:
        await self._vector_store.aping()
