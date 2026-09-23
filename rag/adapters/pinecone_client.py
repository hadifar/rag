import asyncio
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager

from langchain_core.documents import Document
from pinecone import AsyncIndex, Hit, IndexModel, Pinecone, PineconeAsyncio

from rag.config import Settings

_TEXT_FIELD = "text"


def _require_host(description: IndexModel) -> str:
    if not description.host:
        raise RuntimeError(f"Pinecone index {description.name!r} has no host")
    return description.host


def ensure_indexes(settings: Settings) -> None:
    """Idempotent: creates the dense/sparse indexes (Pinecone-embedded, no client-side
    embedding model) only if missing.
    """
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    if not pc.has_index(settings.PINECONE_DENSE_INDEX_NAME):
        pc.create_index_for_model(
            name=settings.PINECONE_DENSE_INDEX_NAME,
            cloud=settings.PINECONE_CLOUD,
            region=settings.PINECONE_REGION,
            embed={
                "model": settings.PINECONE_DENSE_MODEL,
                "field_map": {"text": _TEXT_FIELD},
            },
        )

    sparse_name = settings.PINECONE_SPARSE_INDEX_NAME
    if not pc.has_index(sparse_name):
        pc.create_index_for_model(
            name=sparse_name,
            cloud=settings.PINECONE_CLOUD,
            region=settings.PINECONE_REGION,
            embed={
                "model": settings.PINECONE_SPARSE_MODEL,
                "field_map": {"text": _TEXT_FIELD},
            },
        )


class HybridPineconeVectorStore:
    """Hybrid retrieval over two Pinecone-managed indexes (VectorStorePort)"""

    def __init__(
        self, dense_index: AsyncIndex, sparse_index: AsyncIndex, *, namespace: str
    ):
        self._dense_index = dense_index
        self._sparse_index = sparse_index
        self._namespace = namespace

    async def aadd_documents(
        self, documents: list[Document], *, ids: list[str]
    ) -> list[str]:
        records = [
            {"_id": id_, _TEXT_FIELD: doc.page_content, **doc.metadata}
            for id_, doc in zip(ids, documents, strict=True)
        ]
        await asyncio.gather(
            self._dense_index.upsert_records(
                records=records, namespace=self._namespace
            ),
            self._sparse_index.upsert_records(
                records=records, namespace=self._namespace
            ),
        )
        return ids

    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Document, float]]:
        dense_response, sparse_response = await asyncio.gather(
            self._dense_index.search_records(
                namespace=self._namespace, query={"inputs": {"text": query}, "top_k": k}
            ),
            self._sparse_index.search_records(
                namespace=self._namespace, query={"inputs": {"text": query}, "top_k": k}
            ),
        )
        hits_by_id = {
            hit.id: hit
            for hit in (*sparse_response.result.hits, *dense_response.result.hits)
        }
        fused_scores = _reciprocal_rank_fusion(
            [
                [hit.id for hit in dense_response.result.hits],
                [hit.id for hit in sparse_response.result.hits],
            ]
        )
        ranked_ids = sorted(fused_scores, key=fused_scores.__getitem__, reverse=True)
        return [
            (_to_document(hits_by_id[doc_id]), fused_scores[doc_id])
            for doc_id in ranked_ids[:k]
        ]

    async def aget_document(self, source_id: str) -> Document | None:
        """Reassembles a document from its chunks by source_id, not by guessing chunk
        ids — works whether the chunker produced one record (WholeDocumentChunker) or
        many (MarkdownHeaderChunker). Both indexes hold identical fields (aadd_documents
        upserts the same records to each), so a plain metadata lookup on the dense index
        is enough; this is a lookup, not a ranked search.
        """
        response = await self._dense_index.fetch_by_metadata(
            filter={"source_id": source_id}, namespace=self._namespace
        )
        if not response.vectors:
            return None

        chunks = sorted(
            response.vectors.values(),
            key=lambda v: (v.metadata or {}).get("chunk_index", 0),
        )
        text = "\n\n".join(
            (chunk.metadata or {}).get(_TEXT_FIELD, "") for chunk in chunks
        )
        metadata = {
            k: v for k, v in (chunks[0].metadata or {}).items() if k != _TEXT_FIELD
        }
        return Document(page_content=text, metadata=metadata)


def _reciprocal_rank_fusion(
    rankings: Iterable[Iterable[str]], k: int = 5
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _to_document(hit: Hit) -> Document:
    fields = dict(hit.fields)
    text = fields.pop(_TEXT_FIELD, "")
    return Document(page_content=text, metadata=fields)


@asynccontextmanager
async def open_vector_store(
    settings: Settings,
) -> AsyncGenerator[HybridPineconeVectorStore]:
    """Opens both index connections once for the caller's scope, closing them on exit —
    mirrors the FastAPI lifespan pattern from the async-Pinecone article.
    """
    ensure_indexes(settings)
    async with PineconeAsyncio(api_key=settings.PINECONE_API_KEY) as pc:
        dense_description, sparse_description = await asyncio.gather(
            pc.describe_index(settings.PINECONE_DENSE_INDEX_NAME),
            pc.describe_index(settings.PINECONE_SPARSE_INDEX_NAME),
        )
        dense_host = _require_host(dense_description)
        sparse_host = _require_host(sparse_description)
        async with (
            pc.IndexAsyncio(host=dense_host) as dense_index,
            pc.IndexAsyncio(host=sparse_host) as sparse_index,
        ):
            yield HybridPineconeVectorStore(
                dense_index=dense_index,
                sparse_index=sparse_index,
                namespace=settings.PINECONE_NAMESPACE,
            )
