from rag.domain.errors import DocumentNotFoundError
from rag.domain.models import Chunk
from rag.domain.ports import RerankerPort, VectorStorePort


class RetrievalService:
    def __init__(
        self, vector_store: VectorStorePort, reranker: RerankerPort, top_k: int
    ):
        self._vector_store = vector_store
        self._reranker = reranker
        self._top_k = top_k  # passages a search returns

    async def search(self, query: str) -> list[tuple[Chunk, float]]:
        candidates = await self._vector_store.asimilarity_search_with_score(
            query, k=self._top_k
        )
        return await self._reranker.rerank(query, candidates)

    async def get_document(self, source_id: str) -> Chunk:
        document = await self._vector_store.aget_document(source_id)
        if document is None:
            raise DocumentNotFoundError(source_id)
        return document

    async def ping(self) -> None:
        await self._vector_store.aping()
