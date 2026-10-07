from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import BaseModel

from rag.domain.models import AttachmentFile, Chunk, RunContext
from rag.services.retrieval_service.caching import CachedEmbeddings
from rag.services.retrieval_service.reranking import LlmReranker, NoReranker
from rag.services.retrieval_service.service import RetrievalService
from tests.unit.fakes import FakeCache, FakeEmbeddings


class _JudgingAgent:
    """LLMPort whose structured reply is `verdicts` as (index, relevant) pairs, or
    which raises `error`; records the prompts.
    """

    def __init__(
        self,
        verdicts: list[tuple[int, bool]] | None = None,
        error: Exception | None = None,
    ):
        self.verdicts = verdicts or []
        self.error = error
        self.prompts: list[str] = []

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attachments: Sequence[AttachmentFile] = (),
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return schema.model_validate(
            {"verdicts": [{"index": i, "relevant": r} for i, r in self.verdicts]}
        )


class _VectorStore:
    """VectorStorePort whose search returns the first k of `results`; records the
    queries.
    """

    def __init__(self, results: list[tuple[Chunk, float]]):
        self.results = results
        self.queries: list[str] = []

    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Chunk, float]]:
        self.queries.append(query)
        return self.results[:k]

    async def aget_document(self, source_id: str) -> Chunk | None:
        return None

    async def aping(self) -> None:
        return None


def _candidates(*summaries: str | None) -> list[tuple[Chunk, float]]:
    def chunk(i: int, summary: str | None) -> Chunk:
        metadata: dict[str, Any] = {"source_id": f"doc-{i}"}
        if summary is not None:
            metadata["summary"] = summary
        return Chunk(text=f"text {i}", metadata=metadata)

    return [(chunk(i, s), 0.9 - i / 10) for i, s in enumerate(summaries)]


def _sources(results: list[tuple[Chunk, float]]) -> list[str]:
    return [str(chunk.metadata["source_id"]) for chunk, _score in results]


async def test_keeps_the_relevant_candidates_in_search_order() -> None:
    candidates = _candidates("a", "b", "c", "d")
    agent = _JudgingAgent(verdicts=[(3, True), (0, False), (1, True), (2, False)])

    results = await LlmReranker(agent).rerank("q", candidates)

    assert results == [candidates[1], candidates[3]]  # search scores kept


async def test_prompt_shows_the_query_and_each_summary_by_index() -> None:
    agent = _JudgingAgent(verdicts=[(0, True), (1, True)])

    await LlmReranker(agent).rerank("price?", _candidates("Plans", "Setup"))

    assert "price?" in agent.prompts[0]
    assert "[0] Plans" in agent.prompts[0]
    assert "[1] Setup" in agent.prompts[0]
    assert "text 0" not in agent.prompts[0]  # summary only, never the text


async def test_unjudged_and_unknown_indices_are_dropped() -> None:
    agent = _JudgingAgent(verdicts=[(1, True), (7, True)])  # 0, 2 unjudged; 7 unknown

    results = await LlmReranker(agent).rerank("q", _candidates("a", "b", "c"))

    assert _sources(results) == ["doc-1"]


async def test_no_relevant_candidate_leaves_nothing() -> None:
    agent = _JudgingAgent(verdicts=[(0, False), (1, False)])

    assert await LlmReranker(agent).rerank("q", _candidates("a", "b")) == []


async def test_a_single_candidate_is_judged_too() -> None:
    agent = _JudgingAgent(verdicts=[(0, False)])

    assert await LlmReranker(agent).rerank("q", _candidates("a")) == []
    assert len(agent.prompts) == 1


async def test_llm_failure_raises() -> None:
    agent = _JudgingAgent(error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await LlmReranker(agent).rerank("q", _candidates("a", "b"))


async def test_no_candidates_need_no_llm_call() -> None:
    agent = _JudgingAgent()

    assert await LlmReranker(agent).rerank("q", []) == []
    assert agent.prompts == []


async def test_search_reranks_the_candidates_and_keeps_the_top_k() -> None:
    store = _VectorStore(_candidates("a", "b", "c", "d", "e"))
    agent = _JudgingAgent(verdicts=[(0, False), (1, True), (2, True), (3, True)])
    service = RetrievalService(
        store, LlmReranker(agent), candidates=4, rerank_candidates=2, cache=FakeCache()
    )

    results = await service.search("q")

    assert _sources(results) == ["doc-1", "doc-2"]  # doc-4 never reached the reranker
    assert "[4]" not in agent.prompts[0]


async def test_search_fetches_at_least_as_many_candidates_as_it_keeps() -> None:
    store = _VectorStore(_candidates("a", "b", "c"))
    service = RetrievalService(
        store, NoReranker(), candidates=1, rerank_candidates=3, cache=FakeCache()
    )

    assert len(await service.search("q")) == 3


def test_a_search_returns_the_rerankers_pick_or_every_fetched_passage() -> None:
    store = _VectorStore([])
    reranked = RetrievalService(
        store, NoReranker(), candidates=10, rerank_candidates=5, cache=FakeCache()
    )
    not_reranked = RetrievalService(
        store, NoReranker(), candidates=10, rerank_candidates=0, cache=FakeCache()
    )

    assert reranked.top_k == 5
    assert not_reranked.top_k == 10


async def test_search_without_reranking_keeps_the_vector_order() -> None:
    candidates = _candidates("a", "b")
    service = RetrievalService(
        _VectorStore(candidates),
        NoReranker(),
        candidates=3,
        rerank_candidates=0,
        cache=FakeCache(),
    )

    assert await service.search("q") == candidates


async def test_a_repeated_query_is_answered_from_the_cache() -> None:
    store = _VectorStore(_candidates("a", "b", "c"))
    agent = _JudgingAgent(verdicts=[(0, True), (1, True), (2, True)])
    service = RetrievalService(
        store, LlmReranker(agent), candidates=3, rerank_candidates=2, cache=FakeCache()
    )

    first = await service.search("q")
    # The same once normalized: trailing whitespace is tidied away.
    second = await service.search("q  ")

    assert second == first
    assert store.queries == ["q"]
    assert len(agent.prompts) == 1


async def test_a_failed_rerank_keeps_the_search_order_and_is_not_cached() -> None:
    candidates = _candidates("a", "b", "c")
    cache: FakeCache[list[tuple[Chunk, float]]] = FakeCache()
    service = RetrievalService(
        _VectorStore(candidates),
        LlmReranker(_JudgingAgent(error=RuntimeError("boom"))),
        candidates=3,
        rerank_candidates=2,
        cache=cache,
    )

    assert await service.search("q") == candidates[:2]
    assert cache.puts == []


async def test_a_failing_cache_does_not_fail_the_search() -> None:
    candidates = _candidates("a", "b")
    service = RetrievalService(
        _VectorStore(candidates),
        NoReranker(),
        candidates=2,
        rerank_candidates=0,
        cache=FakeCache(failing=True),
    )

    assert await service.search("q") == candidates


class _CountingEmbeddings(FakeEmbeddings):
    def __init__(self):
        self.queries: list[str] = []

    async def aembed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return await super().aembed_query(text)


async def test_a_query_is_embedded_once_and_documents_every_time() -> None:
    inner = _CountingEmbeddings()
    cache: FakeCache[list[float]] = FakeCache()
    embeddings = CachedEmbeddings(inner, cache)

    first = await embeddings.aembed_query("pricing")
    second = await embeddings.aembed_query("pricing")
    await embeddings.aembed_documents(["pricing"])

    assert second == first
    assert inner.queries == ["pricing"]
    assert cache.puts == ["pricing"]
