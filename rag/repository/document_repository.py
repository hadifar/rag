import json
from collections.abc import Sequence

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import Chunk, IndexedDocument
from rag.domain.ports import EmbeddingsPort

# Reciprocal rank fusion's constant: the higher, the less a top rank outweighs the
# next ones. 60 is the value from the original paper.
_RRF_K = 10

# The k best chunks by reciprocal rank fusion of two rankings, a chunk scoring
# 1 / (rrf_k + rank) in each it appears in:
# * semantic: every chunk, by a weighted sum of two cosine similarities, the query
#   against the chunk's summary and against its text. A chunk without a summary
#   embedding uses its text for both.
# * keyword: the chunks matching any of the query's words in `content_tsv` (all of
#   them would miss on one word absent from the knowledge base), by ts_rank_cd. The
#   words are stemmed once, by to_tsvector, then quoted into the tsquery as they
#   are: to_tsquery would stem them again ('releas' to 'relea'). A query of only
#   stopwords has no words, and this ranking is empty.
# Both rankings are whole, not cut to a top few, so a chunk matching a word always
# beats one matching none. A full scan (an HNSW index can't order by a sum), which
# is fine at knowledge-base size.
_HYBRID_SEARCH = """
WITH query AS (
    SELECT %(embedding)s::vector AS v,
        (
            SELECT string_agg('''' || replace(word, '''', '''''') || '''', ' | ')
            FROM unnest(tsvector_to_array(to_tsvector('english', %(query)s))) AS word
        )::tsquery AS words
),
semantic AS (
    SELECT id, row_number() OVER (ORDER BY score DESC, id) AS rank
    FROM (
        SELECT id,
            (1 - %(summary_weight)s::float8) * (1 - (embedding <=> query.v))
            + %(summary_weight)s::float8
                * (1 - (COALESCE(summary_embedding, embedding) <=> query.v)) AS score
        FROM chunks, query
    ) AS scored
),
keyword AS (
    SELECT id,
        row_number() OVER (ORDER BY ts_rank_cd(content_tsv, query.words) DESC, id)
            AS rank
    FROM chunks, query
    WHERE content_tsv @@ query.words
),
fused AS (
    SELECT id,
        1.0 / (%(rrf_k)s + semantic.rank)
        + COALESCE(1.0 / (%(rrf_k)s + keyword.rank), 0) AS score
    FROM semantic LEFT JOIN keyword USING (id)
)
SELECT id, content, metadata, score
FROM fused JOIN chunks USING (id)
ORDER BY score DESC, id
LIMIT %(k)s
"""

_INSERT_DOCUMENT = "INSERT INTO documents (source_id, content_hash) VALUES (%s, %s)"

_INSERT_CHUNK = """
INSERT INTO chunks
    (id, source_id, chunk_index, content, metadata, embedding, summary_embedding)
VALUES (%s, %s, %s, %s, %s, %s::vector, %s::vector)
"""


class DocumentRepository:
    """Knowledge-base documents, stored as chunks in Postgres (VectorStorePort for
    reads, DocumentIndexPort for ingestion).

    Search is hybrid: pgvector cosine similarity against both a chunk's text and its
    `summary` metadata (`summary_weight` being the summary's share), fused by rank
    with a Postgres full-text match on the chunk's text. Embeddings are computed
    client-side by `embeddings`.
    """

    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection],
        embeddings: EmbeddingsPort,
        *,
        summary_weight: float,
    ):
        self._pool = pool
        self._embeddings = embeddings
        self._summary_weight = summary_weight

    async def alist_content_hashes(self) -> dict[str, str]:
        async with self._pool.connection() as conn:
            cur = await conn.execute("SELECT source_id, content_hash FROM documents")
            return dict(await cur.fetchall())

    async def areplace_documents(
        self, documents: list[IndexedDocument], *, removed: list[str]
    ) -> None:
        """Embeds before opening the transaction, so no connection is held while
        waiting on the embedding API. Deleting a `documents` row cascades to its
        chunks, so a document that shrank leaves no stale chunks behind. Cached search
        results go in the same transaction, so none outlives the index it came from.
        """
        if not documents and not removed:
            return

        chunks = [chunk for document in documents for chunk in document.chunks]
        summaries = [str(chunk.metadata.get("summary", "")) for chunk in chunks]
        # One embedding call: every chunk's text, then the summaries that exist.
        texts = [chunk.text for chunk in chunks] + [s for s in summaries if s]
        vectors = await self._embeddings.aembed_documents(texts) if texts else []
        summary_vectors = iter(vectors[len(chunks) :])
        chunk_rows = [
            (
                chunk.id,
                chunk.metadata["source_id"],
                chunk.metadata["chunk_index"],
                chunk.text,
                Jsonb(chunk.metadata),
                to_vector_literal(vector),
                to_vector_literal(next(summary_vectors)) if summary else None,
            )
            for chunk, summary, vector in zip(
                chunks, summaries, vectors[: len(chunks)], strict=True
            )
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
            await cur.execute("DELETE FROM search_cache")

    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Chunk, float]]:
        embedding = await self._embeddings.aembed_query(query)
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                _HYBRID_SEARCH,
                {
                    "query": query,
                    "embedding": to_vector_literal(embedding),
                    "summary_weight": self._summary_weight,
                    "rrf_k": _RRF_K,
                    "k": k,
                },
            )
            rows = await cur.fetchall()
        return [
            (Chunk(text=content, metadata=metadata, id=chunk_id), float(score))
            for chunk_id, content, metadata, score in rows
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


def to_vector_literal(vector: Sequence[float]) -> str:
    """pgvector's text input format, cast with ::vector in SQL. Avoids registering the
    vector type on every pooled connection, which would fail before the migration ran
    and take auth down with it, since the pool is shared.
    """
    return json.dumps(list(vector), separators=(",", ":"))
