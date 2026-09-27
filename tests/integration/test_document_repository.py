"""Hybrid retrieval against real Postgres (pgvector + full-text) and real embeddings,
over the fixture knowledge base seeded by conftest's `seeded_kb`.
"""

from rag.repository.document_repository import DocumentRepository


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


async def test_reingesting_upserts_instead_of_duplicating(
    seeded_kb: DocumentRepository,
) -> None:
    document = await seeded_kb.aget_document("it-office-plants.md")
    assert document is not None

    await seeded_kb.aadd_documents(
        [
            document.model_copy(
                update={"metadata": {**document.metadata, "chunk_index": 0}}
            )
        ],
        ids=["it-office-plants.md::0"],
    )

    again = await seeded_kb.aget_document("it-office-plants.md")
    assert again is not None and again.page_content == document.page_content


async def test_ping_succeeds_when_the_table_exists(
    seeded_kb: DocumentRepository,
) -> None:
    await seeded_kb.aping()
