"""The Postgres caches: round trips, model isolation, expiry, and the search cache's
join to `chunks` (a removed chunk is left out; ingestion empties it). Over `fake_kb`,
so no embedding call is made.
"""

from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import InputVerdict
from rag.repository.cache_repository import (
    EmbeddingCacheRepository,
    InputVerdictCacheRepository,
    SearchCacheRepository,
)
from rag.repository.document_repository import DocumentRepository

_MODEL = "it-model"
_TTL = timedelta(days=1)


@pytest.fixture(autouse=True)
async def _clean_caches(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[None]:
    yield
    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM embedding_cache WHERE model LIKE 'it-%'")
        await conn.execute("DELETE FROM search_cache WHERE model LIKE 'it-%'")
        await conn.execute("DELETE FROM input_verdict_cache WHERE model LIKE 'it-%'")


async def test_an_embedding_comes_back_as_stored_for_its_model_only(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> None:
    cache = EmbeddingCacheRepository(db_pool, model=_MODEL, ttl=_TTL)
    other_model = EmbeddingCacheRepository(db_pool, model="it-other", ttl=_TTL)
    vector = [0.25, -0.5] * 768

    await cache.put("pricing", vector)

    assert await cache.get("pricing") == vector
    assert await cache.get("security") is None
    assert await other_model.get("pricing") is None


async def test_an_expired_entry_misses(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> None:
    cache = InputVerdictCacheRepository(db_pool, model=_MODEL, ttl=timedelta(0))

    await cache.put("prompt", InputVerdict(reason="about it", decision="allow"))

    assert await cache.get("prompt") is None


async def test_a_verdict_is_overwritten_by_a_later_one(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> None:
    cache = InputVerdictCacheRepository(db_pool, model=_MODEL, ttl=_TTL)
    blocked = InputVerdict(reason="injection", decision="block")

    await cache.put("prompt", InputVerdict(reason="about it", decision="allow"))
    await cache.put("prompt", blocked)

    assert await cache.get("prompt") == blocked


async def test_a_search_comes_back_in_order_for_its_scope_only(
    db_pool: AsyncConnectionPool[AsyncConnection], fake_kb: DocumentRepository
) -> None:
    cache = SearchCacheRepository(db_pool, model=_MODEL, ttl=_TTL, scope="k=3")
    other_scope = SearchCacheRepository(db_pool, model=_MODEL, ttl=_TTL, scope="k=5")
    results = await fake_kb.asimilarity_search_with_score("QX-7731", k=3)

    await cache.put("QX-7731", results)

    assert await cache.get("QX-7731") == results
    assert await other_scope.get("QX-7731") is None


async def test_a_cached_search_leaves_out_a_removed_chunk(
    db_pool: AsyncConnectionPool[AsyncConnection], fake_kb: DocumentRepository
) -> None:
    cache = SearchCacheRepository(db_pool, model=_MODEL, ttl=_TTL)
    results = await fake_kb.asimilarity_search_with_score("QX-7731", k=3)
    await cache.put("QX-7731", results)
    removed = str(results[0][0].metadata["source_id"])

    async with db_pool.connection() as conn:
        # Cascades to its chunks.
        await conn.execute("DELETE FROM documents WHERE source_id = %s", (removed,))

    assert await cache.get("QX-7731") == results[1:]


async def test_ingestion_empties_the_search_cache(
    db_pool: AsyncConnectionPool[AsyncConnection], fake_kb: DocumentRepository
) -> None:
    cache = SearchCacheRepository(db_pool, model=_MODEL, ttl=_TTL)
    results = await fake_kb.asimilarity_search_with_score("QX-7731", k=3)
    await cache.put("QX-7731", results)

    await fake_kb.areplace_documents([], removed=["it-office-plants.md"])

    assert await cache.get("QX-7731") is None
