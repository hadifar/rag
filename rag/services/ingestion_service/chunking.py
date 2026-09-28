from langchain_core.documents import Document

from rag.domain.models import RawDocument


class WholeDocumentChunker:
    """Treats each document as a single chunk (no splitting).

    Chunk ids are deterministic (source_id::0), so re-running ingestion after
    a doc edit upserts over the existing vector instead of duplicating it.
    """

    def chunk(self, document: RawDocument) -> list[Document]:
        text = document.text.strip()
        if not text:
            return []
        return [
            Document(
                id=f"{document.source_id}::0",
                page_content=text,
                metadata={
                    **document.metadata,
                    "source_id": document.source_id,
                    "chunk_index": 0,
                },
            )
        ]
