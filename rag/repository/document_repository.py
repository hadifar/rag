import json
from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import IndexedDocument

RRF_K = 5

# One round trip: the k nearest chunks by cosine distance (HNSW index) and the k best
# full-text matches (GIN index), fused by reciprocal rank. A chunk found by both lists
# scores both terms; one found by only one list scores just that term.
_HYBRID_SEARCH = """
WITH dense AS (
    SELECT id, row_number() OVER (ORDER BY embedding <=> %(embedding)s::vector) AS rank
    FROM chunks
    ORDER BY embedding <=> %(embedding)s::vector
    LIMIT %(k)s
),
sparse AS (
    SELECT id, row_number() OVER (ORDER BY ts_rank_cd(content_tsv, query) DESC) AS rank
    FROM chunks, websearch_to_tsquery('english', %(query)s) AS query
    WHERE content_tsv @@ query
    ORDER BY ts_rank_cd(content_tsv, query) DESC
    LIMIT %(k)s
)
SELECT c.content, c.metadata,
       COALESCE(1.0 / (%(rrf_k)s + dense.rank), 0)
     + COALESCE(1.0 / (%(rrf_k)s + sparse.rank), 0) AS score
FROM dense
FULL OUTER JOIN sparse USING (id)
JOIN chunks AS c USING (id)
ORDER BY score DESC
LIMIT %(k)s
"""

_INSERT_DOCUMENT = "INSERT INTO documents (source_id, content_hash) VALUES (%s, %s)"

_INSERT_CHUNK = """
INSERT INTO chunks (id, source_id, chunk_index, content, metadata, embedding)
VALUES (%s, %s, %s, %s, %s, %s::vector)
"""


class DocumentRepository:
    """Knowledge-base documents, stored as chunks in Postgres (VectorStorePort for
    reads, DocumentIndexPort for ingestion).

    Search is hybrid — pgvector cosine similarity plus Postgres full-text — fused by
    reciprocal rank. Embeddings are computed client-side by `embeddings`.
    """

    def __init__(
        self, pool: AsyncConnectionPool[AsyncConnection], embeddings: Embeddings
    ):
        self._pool = pool
        self._embeddings = embeddings

    async def alist_content_hashes(self) -> dict[str, str]:
        async with self._pool.connection() as conn:
            cur = await conn.execute("SELECT source_id, content_hash FROM documents")
            return dict(await cur.fetchall())

    async def areplace_documents(
        self, documents: list[IndexedDocument], *, removed: list[str]
    ) -> None:
        """Embeds before opening the transaction, so no connection is held while
        waiting on the embedding API. Deleting a `documents` row cascades to its
        chunks, so a document that shrank leaves no stale chunks behind.
        """
        if not documents and not removed:
            return

        chunks = [chunk for document in documents for chunk in document.chunks]
        vectors = (
            await self._embeddings.aembed_documents(
                [chunk.page_content for chunk in chunks]
            )
            if chunks
            else []
        )
        chunk_rows = [
            (
                chunk.id,
                chunk.metadata["source_id"],
                chunk.metadata.get("chunk_index", 0),
                chunk.page_content,
                Jsonb(chunk.metadata),
                _to_vector_literal(vector),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        stale = [*removed, *(document.source_id for document in documents)]

        # One transaction: a failed ingest leaves the previous index intact.
        async with (
            self._pool.connection() as conn,
            conn.transaction(),
            conn.cursor() as cur,
        ):
            await cur.execute(
                "DELETE FROM documents WHERE source_id = ANY(%s)", (stale,)
            )
            if documents:
                await cur.executemany(
                    _INSERT_DOCUMENT,
                    [
                        (document.source_id, document.content_hash)
                        for document in documents
                    ],
                )
            if chunk_rows:
                await cur.executemany(_INSERT_CHUNK, chunk_rows)

    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Document, float]]:
        embedding = await self._embeddings.aembed_query(query)
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                _HYBRID_SEARCH,
                {
                    "embedding": _to_vector_literal(embedding),
                    "query": query,
                    "k": k,
                    "rrf_k": RRF_K,
                },
            )
            rows = await cur.fetchall()
        return [
            (Document(page_content=content, metadata=_metadata(metadata)), float(score))
            for content, metadata, score in rows
        ]

    async def aget_document(self, source_id: str) -> Document | None:
        """Reassembles a document from its chunks, in order — works whether the chunker
        produced one chunk (WholeDocumentChunker) or many (MarkdownHeaderChunker).
        """
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT content, metadata FROM chunks "
                "WHERE source_id = %s ORDER BY chunk_index",
                (source_id,),
            )
            rows = await cur.fetchall()
        if not rows:
            return None
        return Document(
            page_content="\n\n".join(content for content, _ in rows),
            metadata=_metadata(rows[0][1]),
        )

    async def aping(self) -> None:
        """Raises if the chunks table can't be queried. No embedding call, so it's
        free to run on every readiness probe.
        """
        async with self._pool.connection() as conn:
            await conn.execute("SELECT 1 FROM chunks LIMIT 1")


def _to_vector_literal(vector: Sequence[float]) -> str:
    """pgvector's text input format, cast with ::vector in SQL. Avoids registering the
    vector type on every pooled connection, which would fail before the migration ran
    and take auth down with it, since the pool is shared.
    """
    return json.dumps(list(vector), separators=(",", ":"))


def _metadata(value: object) -> dict:
    return value if isinstance(value, dict) else {}
