from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.adapters.langchain.llm_client import build_embeddings, build_llm
from rag.config import Settings
from rag.domain.models import RunContext
from rag.repository.document_repository import DocumentRepository
from rag.services.agent_service.service import AgentService
from rag.services.retrieval_service.reranking import LlmReranker, NoReranker
from rag.services.retrieval_service.service import RetrievalService

EVAL_DIR = Path(__file__).parent

# Rank of the first expected document per question (None for a miss), filled by
# the tests and summarised once the session ends.
RANKS: list[int | None] = []


def _targeted(config: pytest.Config) -> bool:
    """True when `tests/eval` (or a file in it) was named on the command line."""
    for arg in config.args:
        path = Path(arg.split("::")[0]).resolve()
        if path == EVAL_DIR or EVAL_DIR in path.parents:
            return True
    return False


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    """Evals run against the real knowledge base, so a bare `pytest` leaves them out.
    Run them with `pytest tests/eval`.
    """
    return None if _targeted(config) else True


@pytest.fixture(scope="session")
def eval_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields come from .env


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def kb(eval_settings: Settings) -> AsyncGenerator[DocumentRepository]:
    """The knowledge base already ingested into the database in `.env`. Read-only."""
    async with AsyncConnectionPool[AsyncConnection](
        eval_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        yield DocumentRepository(
            pool,
            build_embeddings(eval_settings),
            summary_weight=eval_settings.RETRIEVAL.SUMMARY_WEIGHT,
        )


def _no_tracing(name: str | None, ctx: RunContext | None) -> RunnableConfig:
    return {}


@pytest.fixture(scope="session")
def search(eval_settings: Settings, kb: DocumentRepository) -> RetrievalService:
    """The app's search over `kb`, reranked as `RETRIEVAL__RERANK_CANDIDATES` says, as
    in the container. The reranker's one-shot LLM call needs no memory and no tracing.
    """
    agent_service = AgentService(
        build_llm(eval_settings),
        InMemorySaver(),
        _no_tracing,
        retry_attempts=eval_settings.LLM.RETRY_ATTEMPTS,
    )
    attempts = eval_settings.LLM.RETRY_ATTEMPTS
    retrieval = eval_settings.RETRIEVAL
    reranker = (
        LlmReranker(agent_service, attempts=attempts)
        if retrieval.rerank
        else NoReranker()
    )
    return RetrievalService(
        kb,
        reranker,
        top_k=retrieval.top_k,
        candidates=retrieval.RETRIEVAL_CANDIDATES,
    )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def kb_sources(kb: DocumentRepository) -> set[str]:
    """The `source_id`s ingested into the knowledge base."""
    return set(await kb.alist_content_hashes())


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if not RANKS:
        return
    hits = [rank for rank in RANKS if rank is not None]
    recall = len(hits) / len(RANKS)
    mrr = sum(1 / rank for rank in hits) / len(RANKS)
    settings = Settings()  # pyright: ignore[reportCallIssue] — fields come from .env
    terminalreporter.section("retrieval eval")
    retrieval = settings.RETRIEVAL
    terminalreporter.write_line(
        f"k={retrieval.top_k} of {retrieval.RETRIEVAL_CANDIDATES}"
        f"  rerank={retrieval.rerank}"
    )
    terminalreporter.write_line(f"questions: {len(RANKS)}")
    terminalreporter.write_line(f"recall@k:  {recall:.2f}")
    terminalreporter.write_line(f"MRR:       {mrr:.2f}")
