"""Retrieval quality over the real knowledge base: each question in
`retrieval_questions.jsonl` must find one of its expected documents in the top k
(`RAG__TOP_K`). One JSON object per line:

    {"query": "how much is the analytics add-on?", "expected": ["02-plans-and-pricing.md"]}

`expected` lists `source_id`s; any of them counts as a hit. The session ends with
recall@k and MRR over all questions.
"""

from typing import Any

import pytest

from rag.config import Settings
from rag.repository.document_repository import DocumentRepository
from tests.eval.conftest import RANKS

pytestmark = pytest.mark.asyncio(loop_scope="session")

QUESTIONS: list[dict[str, Any]] = [
    {
        "query": "latest release note AtlasFlow release notes newest release",
        "expected": ["26-release-notes-2026-01.md"],
    }
]


@pytest.mark.parametrize("case", QUESTIONS, ids=[q["query"][:60] for q in QUESTIONS])
async def test_question_finds_an_expected_document(
    kb: DocumentRepository,
    kb_sources: set[str],
    eval_settings: Settings,
    case: dict[str, Any],
) -> None:
    unknown = set(case["expected"]) - kb_sources
    assert not unknown, f"expected documents not in the knowledge base: {unknown}"

    results = await kb.asimilarity_search_with_score(
        case["query"], k=eval_settings.RAG.TOP_K
    )
    sources = [str(chunk.metadata["source_id"]) for chunk, _score in results]
    rank = next(
        (i for i, source in enumerate(sources, start=1) if source in case["expected"]),
        None,
    )
    RANKS.append(rank)

    assert rank is not None, f"expected one of {case['expected']}, got {sources}"
