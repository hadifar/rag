from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from langchain_core.runnables import RunnableConfig
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.adapters.langchain.llm_client import build_embeddings, build_llms
from rag.config import Settings
from rag.domain.models import RunContext
from rag.repository.cache_repository import NoCache
from rag.repository.document_repository import DocumentRepository
from rag.services.agent_service.llm import Llm
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
    in the container. The reranker's one-shot LLM call needs no tracing.
    """
    llm = Llm(build_llms(eval_settings), _no_tracing, eval_settings.LLM.RETRY_ATTEMPTS)
    retrieval = eval_settings.RETRIEVAL
    reranker = LlmReranker(llm) if retrieval.RERANK_CANDIDATES else NoReranker()
    return RetrievalService(
        kb,
        reranker,
        candidates=retrieval.RETRIEVAL_CANDIDATES,
        rerank_candidates=retrieval.RERANK_CANDIDATES,
        # Measured afresh: a cached result would hide a change to retrieval.
        cache=NoCache(),
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
        f"fetched={retrieval.RETRIEVAL_CANDIDATES}"
        f"  reranked to={retrieval.RERANK_CANDIDATES or 'off'}"
    )
    terminalreporter.write_line(f"questions: {len(RANKS)}")
    terminalreporter.write_line(f"recall@k:  {recall:.2f}")
    terminalreporter.write_line(f"MRR:       {mrr:.2f}")
