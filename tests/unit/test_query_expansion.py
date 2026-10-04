from typing import Any

from pydantic import BaseModel

from rag.domain.models import AgentSpec, Chunk, RunContext
from rag.domain.ports import ChatAgentPort
from rag.services.retrieval_service.expansion import LlmQueryExpander, NoQueryExpander
from rag.services.retrieval_service.reranking import NoReranker
from rag.services.retrieval_service.service import RetrievalService


class _RewritingAgent:
    """AgentServicePort whose structured reply is `queries`, or which raises `error`;
    records the prompts.
    """

    def __init__(
        self, queries: list[str] | None = None, error: Exception | None = None
    ):
        self.queries = queries or []
        self.error = error
        self.prompts: list[str] = []

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return schema.model_validate({"queries": self.queries})

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        raise NotImplementedError("the expander only asks for structured replies")

    def create_agent(self, spec: AgentSpec) -> ChatAgentPort:
        raise NotImplementedError("the stub builds no agent")


class _FixedExpander:
    """QueryExpanderPort that returns `variants` for any query."""

    def __init__(self, variants: list[str]):
        self.variants = variants

    async def expand(self, query: str) -> list[str]:
        return self.variants


class _VectorStore:
    """VectorStorePort that returns the first k of `results[query]`; records queries."""

    def __init__(self, results: dict[str, list[tuple[Chunk, float]]]):
        self.results = results
        self.queries: list[str] = []

    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Chunk, float]]:
        self.queries.append(query)
        return self.results.get(query, [])[:k]

    async def aget_document(self, source_id: str) -> Chunk | None:
        return None

    async def aping(self) -> None:
        return None


def _found(*hits: tuple[str, float]) -> list[tuple[Chunk, float]]:
    def chunk(source: str) -> Chunk:
        metadata: dict[str, Any] = {"source_id": source}
        return Chunk(text=f"text of {source}", metadata=metadata)

    return [(chunk(source), score) for source, score in hits]


def _sources(results: list[tuple[Chunk, float]]) -> list[str]:
    return [str(chunk.metadata["source_id"]) for chunk, _score in results]


async def test_returns_the_llms_rewrites() -> None:
    agent = _RewritingAgent(queries=["billing cost", "subscription fee"])

    variants = await LlmQueryExpander(agent, count=2, attempts=1).expand("price?")

    assert variants == ["billing cost", "subscription fee"]
    assert "price?" in agent.prompts[0]
    assert "2 different ways" in agent.prompts[0]


async def test_drops_blank_repeated_and_original_queries() -> None:
    agent = _RewritingAgent(queries=[" Price? ", "", "fees", "FEES", "  "])

    variants = await LlmQueryExpander(agent, count=3, attempts=1).expand("price?")

    assert variants == ["fees"]


async def test_keeps_at_most_count_rewrites() -> None:
    agent = _RewritingAgent(queries=["a", "b", "c"])

    assert await LlmQueryExpander(agent, count=2, attempts=1).expand("q") == ["a", "b"]


async def test_llm_failure_gives_no_rewrites() -> None:
    agent = _RewritingAgent(error=RuntimeError("boom"))

    assert await LlmQueryExpander(agent, count=2, attempts=1).expand("q") == []


async def test_no_expander_gives_no_rewrites() -> None:
    assert await NoQueryExpander().expand("q") == []


async def test_search_runs_the_query_and_each_rewrite() -> None:
    store = _VectorStore({})
    service = RetrievalService(
        store, _FixedExpander(["v1", "v2"]), NoReranker(), top_k=3
    )

    await service.search("q")

    assert sorted(store.queries) == ["q", "v1", "v2"]


async def test_search_merges_passages_once_each_by_best_score() -> None:
    store = _VectorStore(
        {
            "q": _found(("a", 0.9), ("b", 0.5)),
            "v1": _found(("b", 0.8), ("c", 0.7)),
        }
    )
    service = RetrievalService(store, _FixedExpander(["v1"]), NoReranker(), top_k=5)

    results = await service.search("q")

    assert _sources(results) == ["a", "b", "c"]
    assert [score for _chunk, score in results] == [0.9, 0.8, 0.7]


async def test_search_keeps_the_best_top_k_of_the_merged_passages() -> None:
    store = _VectorStore(
        {
            "q": _found(("a", 0.6), ("b", 0.5)),
            "v1": _found(("c", 0.9), ("d", 0.4)),
        }
    )
    service = RetrievalService(store, _FixedExpander(["v1"]), NoReranker(), top_k=2)

    assert _sources(await service.search("q")) == ["c", "a"]
