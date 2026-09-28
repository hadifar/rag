"""Hybrid retrieval against real Postgres (pgvector + full-text) and real embeddings,
over the fixture knowledge base seeded by conftest's `seeded_kb`.
"""

from pathlib import Path

from langchain_core.documents import Document
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.domain.models import IndexedDocument
from rag.repository.document_repository import DocumentRepository
from rag.services.ingestion_service.loaders import MarkdownFileLoader
from tests.integration.conftest import FIXTURE_KB, ingestion_service


async def _top_sources(repository: DocumentRepository, query: str) -> list[str]:
    results = await repository.asimilarity_search_with_score(query, k=3)
    return [doc.metadata["source_id"] for doc, _score in results]


async def test_semantic_query_finds_the_document_without_shared_keywords(
    seeded_kb: DocumentRepository,
) -> None:
    sources = await _top_sources(seeded_kb, "how expensive is the analytics extension?")
    assert sources[0] == "it-plans-and-pricing.md"


async def test_exact_error_code_is_found_by_the_keyword_side(
    seeded_kb: DocumentRepository,
) -> None:
    sources = await _top_sources(seeded_kb, "QX-7731")
    assert sources[0] == "it-sso-troubleshooting.md"


async def test_results_are_ranked_best_first(seeded_kb: DocumentRepository) -> None:
    results = await seeded_kb.asimilarity_search_with_score("Gustavo the ficus", k=3)
    scores = [score for _doc, score in results]
    assert results[0][0].metadata["source_id"] == "it-office-plants.md"
    assert scores == sorted(scores, reverse=True)


async def test_get_document_reassembles_chunks_in_order(
    seeded_kb: DocumentRepository,
) -> None:
    document = await seeded_kb.aget_document("it-plans-and-pricing.md")

    assert document is not None
    # MarkdownHeaderChunker split it into three sections; they come back in order.
    assert (
        document.page_content.index("# AtlasFlow Plans")
        < document.page_content.index("## Starter")
        < document.page_content.index("## Zephyr")
    )
    assert await seeded_kb.aget_document("it-does-not-exist.md") is None


async def test_reingesting_unchanged_documents_embeds_nothing(
    seeded_kb: DocumentRepository,
    db_pool: AsyncConnectionPool[AsyncConnection],
    tmp_path: Path,
) -> None:
    service = ingestion_service(seeded_kb, db_pool, tmp_path)
    report = await service.ingest(MarkdownFileLoader(FIXTURE_KB), remove_missing=False)

    assert (report.added, report.updated, report.chunks) == (0, 0, 0)
    assert report.unchanged == 3


async def test_replacing_a_document_drops_its_old_chunks(
    seeded_kb: DocumentRepository,
) -> None:
    source_id = "it-plans-and-pricing.md"  # three chunks, shrinking to one
    chunk = Document(
        id=f"{source_id}::0",
        page_content="# Replaced",
        metadata={"source_id": source_id, "chunk_index": 0},
    )

    await seeded_kb.areplace_documents(
        [IndexedDocument(source_id, "new-hash", [chunk])], removed=[]
    )

    document = await seeded_kb.aget_document(source_id)
    assert document is not None and document.page_content == "# Replaced"
    assert (await seeded_kb.alist_content_hashes())[source_id] == "new-hash"


async def test_removing_a_document_deletes_it_and_its_chunks(
    seeded_kb: DocumentRepository,
) -> None:
    await seeded_kb.areplace_documents([], removed=["it-office-plants.md"])

    assert await seeded_kb.aget_document("it-office-plants.md") is None
    assert "it-office-plants.md" not in await seeded_kb.alist_content_hashes()


async def test_ping_succeeds_when_the_table_exists(
    seeded_kb: DocumentRepository,
) -> None:
    await seeded_kb.aping()
