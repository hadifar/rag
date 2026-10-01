from rag.domain.errors import DocumentNotFoundError
from rag.domain.models import Chunk
from rag.domain.ports import VectorStorePort


class RetrievalService:
    def __init__(self, vector_store: VectorStorePort, top_k: int):
        self._vector_store = vector_store
        self._top_k = top_k  # passages a search returns

    async def search(self, query: str) -> list[tuple[Chunk, float]]:
        return await self._vector_store.asimilarity_search_with_score(
            query, k=self._top_k
        )

    async def get_document(self, source_id: str) -> Chunk:
        document = await self._vector_store.aget_document(source_id)
        if document is None:
            raise DocumentNotFoundError(source_id)
        return document

    async def ping(self) -> None:
        await self._vector_store.aping()
