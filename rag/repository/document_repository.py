import json
from collections.abc import Sequence

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import Chunk, IndexedDocument
from rag.domain.ports import EmbeddingsPort

# The k nearest chunks by cosine distance (HNSW index), scored as cosine similarity.
_VECTOR_SEARCH = """
SELECT content, metadata, 1 - (embedding <=> %(embedding)s::vector) AS score
FROM chunks
ORDER BY embedding <=> %(embedding)s::vector
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

    Search is pgvector cosine similarity. Embeddings are computed client-side by
    `embeddings`.
    """

    def __init__(
        self, pool: AsyncConnectionPool[AsyncConnection], embeddings: EmbeddingsPort
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
            await self._embeddings.aembed_documents([chunk.text for chunk in chunks])
            if chunks
            else []
        )
        chunk_rows = [
            (
                chunk.id,
                chunk.metadata["source_id"],
                chunk.metadata["chunk_index"],
                chunk.text,
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
    ) -> list[tuple[Chunk, float]]:
        embedding = await self._embeddings.aembed_query(query)
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                _VECTOR_SEARCH,
                {"embedding": _to_vector_literal(embedding), "k": k},
            )
            rows = await cur.fetchall()
        return [
            (Chunk(text=content, metadata=metadata), float(score))
            for content, metadata, score in rows
        ]

    async def aget_document(self, source_id: str) -> Chunk | None:
        """Reassembles a document from its chunks, in order, so it doesn't depend on
        how many chunks the chunker cut it into.
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
        return Chunk(
            text="\n\n".join(content for content, _ in rows),
            metadata=rows[0][1],
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
