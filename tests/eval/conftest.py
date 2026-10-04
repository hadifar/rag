from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.adapters.lang_llm_client import build_embeddings
from rag.config import Settings
from rag.repository.document_repository import DocumentRepository

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
    terminalreporter.section("retrieval eval")
    terminalreporter.write_line(f"questions: {len(RANKS)}")
    terminalreporter.write_line(f"recall@k:  {recall:.2f}")
    terminalreporter.write_line(f"MRR:       {mrr:.2f}")
