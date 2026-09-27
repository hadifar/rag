import json
from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

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

_UPSERT = """
INSERT INTO chunks (id, source_id, chunk_index, content, metadata, embedding)
VALUES (%s, %s, %s, %s, %s, %s::vector)
ON CONFLICT (id) DO UPDATE SET
    source_id = EXCLUDED.source_id,
    chunk_index = EXCLUDED.chunk_index,
    content = EXCLUDED.content,
    metadata = EXCLUDED.metadata,
    embedding = EXCLUDED.embedding
"""


class DocumentRepository:
    """Knowledge-base documents, stored as chunks in Postgres (VectorStorePort).

    Search is hybrid — pgvector cosine similarity plus Postgres full-text — fused by
    reciprocal rank. Embeddings are computed client-side by `embeddings`.
    """

    def __init__(
        self, pool: AsyncConnectionPool[AsyncConnection], embeddings: Embeddings
    ):
        self._pool = pool
        self._embeddings = embeddings

    async def aadd_documents(
        self, documents: list[Document], *, ids: list[str]
    ) -> list[str]:
        vectors = await self._embeddings.aembed_documents(
            [doc.page_content for doc in documents]
        )
        rows = [
            (
                id_,
                doc.metadata["source_id"],
                doc.metadata.get("chunk_index", 0),
                doc.page_content,
                Jsonb(doc.metadata),
                _to_vector_literal(vector),
            )
            for id_, doc, vector in zip(ids, documents, vectors, strict=True)
        ]
        # One transaction: a failed ingest leaves the previous chunks intact.
        async with (
            self._pool.connection() as conn,
            conn.transaction(),
            conn.cursor() as cur,
        ):
            await cur.executemany(_UPSERT, rows)
        return ids

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
