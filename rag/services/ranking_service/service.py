from langchain_core.documents import Document

from rag.domain.ports import VectorStorePort


class RankingService:
    def __init__(self, vector_store: VectorStorePort):
        self._vector_store = vector_store

    async def search(self, query: str, top_k: int = 5) -> list[tuple[Document, float]]:
        return await self._vector_store.asimilarity_search_with_score(query, k=top_k)
