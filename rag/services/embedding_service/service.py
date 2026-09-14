from rag.domain.ports import EmbedderPort


class EmbeddingService:
    def __init__(self, embedder: EmbedderPort):
        self._embedder = embedder

    async def embed_query(self, text: str) -> list[float]:
        return await self._embedder.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embedder.aembed_documents(texts)
