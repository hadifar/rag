from typing import Any

from pydantic import BaseModel

from rag.domain.models import Chunk, RunContext
from rag.services.retrieval_service.reranking import LlmReranker, NoReranker
from rag.services.retrieval_service.service import RetrievalService


class _ScoringAgent:
    """LLMPort whose structured reply is `scores` as (index, score) pairs, or
    which raises `error`; records the prompts.
    """

    def __init__(
        self,
        scores: list[tuple[int, int]] | None = None,
        error: Exception | None = None,
    ):
        self.scores = scores or []
        self.error = error
        self.prompts: list[str] = []

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return schema.model_validate(
            {"scores": [{"index": i, "score": s} for i, s in self.scores]}
        )


class _VectorStore:
    """VectorStorePort whose search returns the first k of `results`."""

    def __init__(self, results: list[tuple[Chunk, float]]):
        self.results = results

    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Chunk, float]]:
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


async def test_orders_candidates_by_the_llms_score() -> None:
    agent = _ScoringAgent(scores=[(0, 2), (1, 9), (2, 5)])
    reranker = LlmReranker(agent)

    results = await reranker.rerank("q", _candidates("a", "b", "c"))

    assert _sources(results) == ["doc-1", "doc-2", "doc-0"]
    assert [score for _chunk, score in results] == [9.0, 5.0, 2.0]


async def test_prompt_shows_the_query_and_each_summary_by_index() -> None:
    agent = _ScoringAgent(scores=[(0, 1), (1, 1)])

    await LlmReranker(agent).rerank("price?", _candidates("Plans", "Setup"))

    assert "price?" in agent.prompts[0]
    assert "[0] Plans" in agent.prompts[0]
    assert "[1] Setup" in agent.prompts[0]
    assert "text 0" not in agent.prompts[0]  # summary only, never the text


async def test_ties_keep_the_search_order() -> None:
    agent = _ScoringAgent(scores=[(0, 7), (1, 7), (2, 7)])

    results = await LlmReranker(agent).rerank("q", _candidates("a", "b", "c"))

    assert _sources(results) == ["doc-0", "doc-1", "doc-2"]


async def test_unscored_and_unknown_indices_sink_below_scored_ones() -> None:
    agent = _ScoringAgent(scores=[(1, 3), (7, 10)])  # 0 and 2 unscored, 7 unknown

    results = await LlmReranker(agent).rerank("q", _candidates("a", "b", "c"))

    assert _sources(results) == ["doc-1", "doc-0", "doc-2"]
    assert [score for _chunk, score in results] == [3.0, 0.0, 0.0]


async def test_out_of_range_scores_are_clamped() -> None:
    agent = _ScoringAgent(scores=[(0, -4), (1, 42)])

    results = await LlmReranker(agent).rerank("q", _candidates("a", "b"))

    assert [score for _chunk, score in results] == [10.0, 1.0]


async def test_llm_failure_keeps_the_candidates_as_given() -> None:
    candidates = _candidates("a", "b")
    agent = _ScoringAgent(error=RuntimeError("boom"))

    assert await LlmReranker(agent).rerank("q", candidates) == candidates


async def test_a_single_candidate_needs_no_llm_call() -> None:
    candidates = _candidates("a")
    agent = _ScoringAgent()

    assert await LlmReranker(agent).rerank("q", candidates) == candidates
    assert agent.prompts == []


async def test_search_reranks_the_candidates_and_keeps_the_top_k() -> None:
    store = _VectorStore(_candidates("a", "b", "c", "d", "e"))
    agent = _ScoringAgent(scores=[(0, 1), (1, 2), (2, 3), (3, 9)])
    service = RetrievalService(
        store, LlmReranker(agent), candidates=4, rerank_candidates=2
    )

    results = await service.search("q")

    assert _sources(results) == ["doc-3", "doc-2"]  # doc-4 never reached the reranker
    assert "[4]" not in agent.prompts[0]


async def test_search_fetches_at_least_as_many_candidates_as_it_keeps() -> None:
    store = _VectorStore(_candidates("a", "b", "c"))
    service = RetrievalService(store, NoReranker(), candidates=1, rerank_candidates=3)

    assert len(await service.search("q")) == 3


def test_a_search_returns_the_rerankers_pick_or_every_fetched_passage() -> None:
    store = _VectorStore([])
    reranked = RetrievalService(store, NoReranker(), candidates=10, rerank_candidates=5)
    not_reranked = RetrievalService(
        store, NoReranker(), candidates=10, rerank_candidates=0
    )

    assert reranked.top_k == 5
    assert not_reranked.top_k == 10


async def test_search_without_reranking_keeps_the_vector_order() -> None:
    candidates = _candidates("a", "b")
    service = RetrievalService(
        _VectorStore(candidates), NoReranker(), candidates=3, rerank_candidates=0
    )

    assert await service.search("q") == candidates
