from typing import Any

import pytest

from rag.services.retrieval_service.service import RetrievalService
from tests.eval.conftest import RANKS

pytestmark = pytest.mark.asyncio(loop_scope="session")

QUESTIONS: list[dict[str, Any]] = [
    {
        "query": "latest release note release notes newest release",
        "expected": ["26-release-notes-2026-01.md"],
    }
]


@pytest.mark.parametrize("case", QUESTIONS, ids=[q["query"][:60] for q in QUESTIONS])
async def test_question_finds_an_expected_document(
    search: RetrievalService,
    kb_sources: set[str],
    case: dict[str, Any],
) -> None:
    unknown = set(case["expected"]) - kb_sources
    assert not unknown, f"expected documents not in the knowledge base: {unknown}"

    results = await search.search(case["query"])
    sources = [str(chunk.metadata["source_id"]) for chunk, _score in results]
    rank = next(
        (i for i, source in enumerate(sources, start=1) if source in case["expected"]),
        None,
    )
    RANKS.append(rank)

    assert rank is not None, f"expected one of {case['expected']}, got {sources}"
