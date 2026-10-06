from rag.domain.errors import DocumentNotFoundError
from rag.domain.models import Chunk
from rag.domain.ports import RerankerPort, VectorStorePort


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStorePort,
        reranker: RerankerPort,
        candidates: int,
        rerank_candidates: int,
    ):
        """`candidates` passages are fetched; the reranker keeps `rerank_candidates` of
        them, or all of them at 0 (no reranking).
        """
        self._vector_store = vector_store
        self._reranker = reranker
        self.top_k = rerank_candidates or candidates  # passages a search returns
        self._candidates = max(candidates, self.top_k)  # passages the reranker sees

    async def search(self, query: str) -> list[tuple[Chunk, float]]:
        """Finds the best `candidates` passages for `query`, reranks them against it
        and returns the first `top_k`.
        """
        candidates = await self._vector_store.asimilarity_search_with_score(
            query, k=self._candidates
        )
        reranked = await self._reranker.rerank(query, candidates)
        return reranked[: self.top_k]

    async def get_document(self, source_id: str) -> Chunk:
        document = await self._vector_store.aget_document(source_id)
        if document is None:
            raise DocumentNotFoundError(source_id)
        return document

    async def ping(self) -> None:
        await self._vector_store.aping()
