"""Vector retrieval and storage correctness against real Postgres (pgvector), over
the fixture knowledge base. Tests that assert on embedding semantics/ranking use
`seeded_kb` (real embeddings); storage/SQL-plumbing tests use `fake_kb`
(deterministic, no network) since they don't care about vector quality.
"""

from pathlib import Path

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import Chunk, IndexedDocument
from rag.repository.document_repository import DocumentRepository
from rag.services.ingestion_service.loaders import load_directory
from tests.integration.conftest import FIXTURE_KB, ingestion_service


async def _top_sources(repository: DocumentRepository, query: str) -> list[str]:
    results = await repository.asimilarity_search_with_score(query, k=3)
    return [str(doc.metadata["source_id"]) for doc, _score in results]


async def test_semantic_query_finds_the_document_without_shared_keywords(
    seeded_kb: DocumentRepository,
) -> None:
    sources = await _top_sources(seeded_kb, "how expensive is the analytics extension?")
    assert sources[0] == "it-plans-and-pricing.md"


async def test_results_are_ranked_best_first(seeded_kb: DocumentRepository) -> None:
    results = await seeded_kb.asimilarity_search_with_score("Gustavo the ficus", k=3)
    scores = [score for _doc, score in results]
    assert results[0][0].metadata["source_id"] == "it-office-plants.md"
    assert scores == sorted(scores, reverse=True)


async def test_get_document_returns_the_whole_document(
    fake_kb: DocumentRepository,
) -> None:
    document = await fake_kb.aget_document("it-plans-and-pricing.md")

    assert document is not None
    assert (
        document.text.index("# AtlasFlow Plans")
        < document.text.index("## Starter")
        < document.text.index("## Zephyr")
    )
    assert await fake_kb.aget_document("it-does-not-exist.md") is None


async def test_reingesting_unchanged_documents_embeds_nothing(
    fake_kb: DocumentRepository,
    db_pool: AsyncConnectionPool[AsyncConnection],
    tmp_path: Path,
) -> None:
    service = ingestion_service(fake_kb, db_pool, tmp_path)
    report = await service.ingest(load_directory(FIXTURE_KB), remove_missing=False)

    assert (report.added, report.updated, report.chunks) == (0, 0, 0)
    assert report.unchanged == 3


async def test_replacing_a_document_drops_its_old_chunks(
    fake_kb: DocumentRepository,
) -> None:
    source_id = "it-plans-and-pricing.md"
    chunk = Chunk(
        id=f"{source_id}::0",
        text="# Replaced",
        metadata={"source_id": source_id, "chunk_index": 0},
    )

    await fake_kb.areplace_documents(
        [IndexedDocument(source_id, "new-hash", [chunk])], removed=[]
    )

    document = await fake_kb.aget_document(source_id)
    assert document is not None
    assert document.text == "# Replaced"
    assert (await fake_kb.alist_content_hashes())[source_id] == "new-hash"


async def test_removing_a_document_deletes_it_and_its_chunks(
    fake_kb: DocumentRepository,
) -> None:
    await fake_kb.areplace_documents([], removed=["it-office-plants.md"])

    assert await fake_kb.aget_document("it-office-plants.md") is None
    assert "it-office-plants.md" not in await fake_kb.alist_content_hashes()


async def test_ping_succeeds_when_the_table_exists(
    fake_kb: DocumentRepository,
) -> None:
    await fake_kb.aping()
