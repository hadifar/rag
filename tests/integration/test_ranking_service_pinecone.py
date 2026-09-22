from rag.adapters.pinecone_client import open_vector_store
from rag.services.retrieval_service.service import RetrievalService


async def _top_source_ids(
    integration_settings, query: str, top_k: int = 3
) -> set[str | None]:
    async with open_vector_store(integration_settings) as vector_store:
        results = await RetrievalService(vector_store=vector_store).search(
            query, top_k=top_k
        )
    return {doc.metadata.get("source_id") for doc, _score in results}


async def test_search_retrives_the_relevant_doc_for_similar_docs(integration_settings):
    source_ids = await _top_source_ids(integration_settings, "latest release note")
    assert "27-release-notes-2025-10.md" in source_ids


async def test_search_matches_h1_title_level_query(integration_settings):
    source_ids = await _top_source_ids(
        integration_settings, "AtlasFlow Plans and Pricing"
    )
    assert "02-plans-and-pricing.md" in source_ids


async def test_search_matches_h2_section_level_query(integration_settings):
    source_ids = await _top_source_ids(
        integration_settings, "feature summary by topic across AtlasFlow plans"
    )
    assert "02-plans-and-pricing.md" in source_ids


async def test_search_matches_h3_subsection_level_query(integration_settings):
    source_ids = await _top_source_ids(
        integration_settings,
        "how long is audit event history retained on the Growth plan?",
    )
    assert "02-plans-and-pricing.md" in source_ids
