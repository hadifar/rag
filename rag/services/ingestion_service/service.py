from rag.domain.models import IngestionReport
from rag.domain.ports import ChunkerPort, DocumentLoaderPort, VectorStorePort


class IngestionService:
    def __init__(self, vector_store: VectorStorePort, chunker: ChunkerPort):
        self._vector_store = vector_store
        self._chunker = chunker

    async def ingest(self, loader: DocumentLoaderPort) -> IngestionReport:
        documents = list(loader.load())
        chunks = [
            chunk for document in documents for chunk in self._chunker.chunk(document)
        ]

        if chunks:
            ids = [chunk.id for chunk in chunks if chunk.id is not None]
            await self._vector_store.aadd_documents(chunks, ids=ids)

        return IngestionReport(documents=len(documents), chunks=len(chunks))
