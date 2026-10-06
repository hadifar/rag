import hashlib
import json
from datetime import timedelta
from typing import Any, ClassVar, LiteralString

from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import Chunk, InputVerdict
from rag.repository.document_repository import to_vector_literal

# Expired rows each write deletes on its way, so the tables stay small without a job.
_CLEANUP_BATCH = 100


class _PostgresCache:
    """A CachePort over one of the cache tables: a row per (model, sha256 of the key),
    kept for `ttl`. Rows of another model are never read; they expire like the rest.
    `scope` is hashed in with every key: whatever else, besides the model, shapes a
    value, so a value made under other settings is never read either.
    """

    table: ClassVar[LiteralString]

    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection],
        *,
        model: str,
        ttl: timedelta,
        scope: str = "",
    ):
        self._pool = pool
        self._model = model
        self._scope = scope
        self._ttl = ttl
        # The ctid subquery bounds the batch: DELETE itself has no LIMIT.
        self._cleanup = sql.SQL(
            "DELETE FROM {table} WHERE ctid = ANY(ARRAY("
            "SELECT ctid FROM {table} WHERE expires_at <= now() LIMIT {batch}))"
        ).format(table=sql.Identifier(self.table), batch=_CLEANUP_BATCH)

    def _params(self, key: str, **values: Any) -> dict[str, Any]:
        return {
            "model": self._model,
            "key": hashlib.sha256(f"{self._scope}\n{key}".encode()).digest(),
            "ttl": self._ttl,
            **values,
        }

    async def _fetch_all(self, query: LiteralString, key: str) -> list[tuple[Any, ...]]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(query, self._params(key))
            return await cur.fetchall()

    async def _write(self, query: LiteralString, key: str, **values: Any) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(query, self._params(key, **values))
            await conn.execute(self._cleanup)


class EmbeddingCacheRepository(_PostgresCache):
    """CachePort of query embeddings, by the query's text."""

    table = "embedding_cache"

    async def get(self, key: str) -> list[float] | None:
        rows = await self._fetch_all(
            "SELECT embedding::text FROM embedding_cache "
            "WHERE model = %(model)s AND key = %(key)s AND expires_at > now()",
            key,
        )
        # pgvector's text output is a JSON array.
        return json.loads(rows[0][0]) if rows else None

    async def put(self, key: str, value: list[float]) -> None:
        await self._write(
            """
            INSERT INTO embedding_cache (model, key, embedding, expires_at)
            VALUES (%(model)s, %(key)s, %(embedding)s::vector, now() + %(ttl)s)
            ON CONFLICT (model, key) DO UPDATE
            SET embedding = EXCLUDED.embedding, created_at = now(),
                expires_at = EXCLUDED.expires_at
            """,
            key,
            embedding=to_vector_literal(value),
        )


class SearchCacheRepository(_PostgresCache):
    """CachePort of search results, by the query. Keeps each passage's chunk id and
    score; a hit reads the chunks themselves, in the order kept, leaving out any that
    are gone. Ingestion empties it (see `DocumentRepository.areplace_documents`).
    """

    table = "search_cache"

    async def get(self, key: str) -> list[tuple[Chunk, float]] | None:
        rows = await self._fetch_all(
            """
            SELECT chunks.id, chunks.content, chunks.metadata, ranked.score
            FROM search_cache,
                unnest(search_cache.chunk_ids, search_cache.scores)
                    WITH ORDINALITY AS ranked (id, score, position)
            JOIN chunks ON chunks.id = ranked.id
            WHERE search_cache.model = %(model)s AND search_cache.key = %(key)s
                AND search_cache.expires_at > now()
            ORDER BY ranked.position
            """,
            key,
        )
        if not rows:
            return None
        return [
            (Chunk(text=content, metadata=metadata, id=chunk_id), float(score))
            for chunk_id, content, metadata, score in rows
        ]

    async def put(self, key: str, value: list[tuple[Chunk, float]]) -> None:
        chunk_ids = [chunk.id for chunk, _score in value]
        if None in chunk_ids:
            raise ValueError("Can't cache a search result with a chunk without an id")
        await self._write(
            """
            INSERT INTO search_cache (model, key, chunk_ids, scores, expires_at)
            VALUES (%(model)s, %(key)s, %(chunk_ids)s, %(scores)s, now() + %(ttl)s)
            ON CONFLICT (model, key) DO UPDATE
            SET chunk_ids = EXCLUDED.chunk_ids, scores = EXCLUDED.scores,
                created_at = now(), expires_at = EXCLUDED.expires_at
            """,
            key,
            chunk_ids=chunk_ids,
            scores=[score for _chunk, score in value],
        )


class InputVerdictCacheRepository(_PostgresCache):
    """CachePort of the off-topic guard's verdicts, by the classifier's prompt."""

    table = "input_verdict_cache"

    async def get(self, key: str) -> InputVerdict | None:
        rows = await self._fetch_all(
            "SELECT decision, reason FROM input_verdict_cache "
            "WHERE model = %(model)s AND key = %(key)s AND expires_at > now()",
            key,
        )
        if not rows:
            return None
        decision, reason = rows[0]
        return InputVerdict.model_validate({"decision": decision, "reason": reason})

    async def put(self, key: str, value: InputVerdict) -> None:
        await self._write(
            """
            INSERT INTO input_verdict_cache (model, key, decision, reason, expires_at)
            VALUES (%(model)s, %(key)s, %(decision)s, %(reason)s, now() + %(ttl)s)
            ON CONFLICT (model, key) DO UPDATE
            SET decision = EXCLUDED.decision, reason = EXCLUDED.reason,
                created_at = now(), expires_at = EXCLUDED.expires_at
            """,
            key,
            decision=value.decision,
            reason=value.reason,
        )


class NoCache:
    """CachePort that keeps nothing, for any value type: with caching turned off."""

    async def get(self, key: str) -> Any:
        return None

    async def put(self, key: str, value: Any) -> None:
        return None
