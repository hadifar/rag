from rag.domain.ports import CachePort, EmbeddingsPort
from rag.shared.resilience import or_default


class CachedEmbeddings:
    """EmbeddingsPort that keeps each query's vector in `cache`. Documents are embedded
    afresh: ingestion embeds each text once, so caching them would only fill the cache.
    """

    def __init__(self, embeddings: EmbeddingsPort, cache: CachePort[list[float]]):
        self._embeddings = embeddings
        self._cache = cache

    async def aembed_query(self, text: str) -> list[float]:
        if cached := await or_default(self._cache.get(text), None):
            return cached
        vector = await self._embeddings.aembed_query(text)
        await or_default(self._cache.put(text, vector), None)
        return vector

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)
