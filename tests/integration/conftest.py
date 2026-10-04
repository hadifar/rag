import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from pydantic import ValidationError

from rag.adapters.kb_archive_store import LocalArchiveStore
from rag.adapters.lang_llm_client import build_embeddings
from rag.config import RetrievalConfig, Settings
from rag.repository.document_repository import DocumentRepository
from rag.repository.ingestion_run_repository import IngestionRunRepository
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.loaders import load_directory
from rag.services.ingestion_service.service import IngestionService
from tests.unit.fakes import FakeEmbeddings

FIXTURE_KB = Path(__file__).parent / "fixtures" / "kb"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """All integration tests share one event loop, so the session-scoped
    `seeded_kb` fixture (real embeddings, seeded once) can be used by async tests
    without a pytest-asyncio loop-scope mismatch.
    """
    for item in items:
        item.add_marker(pytest.mark.asyncio(loop_scope="session"))


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """Real Settings loaded from .env (or CI's env): real Postgres and LLM provider.

    Skips locally when credentials are missing, but fails in CI: a skipped run there
    reports green with zero tests executed.
    """
    try:
        return Settings()  # pyright: ignore[reportCallIssue] — fields come from .env
    except ValidationError as exc:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Postgres/LLM settings not configured in .env: {exc}")


@pytest.fixture
async def db_pool(
    integration_settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        yield pool


def ingestion_service(
    repository: DocumentRepository,
    db_pool: AsyncConnectionPool[AsyncConnection],
    tmp_path: Path,
) -> IngestionService:
    return IngestionService(
        repository,
        WholeDocumentChunker(),
        LocalArchiveStore(tmp_path),
        IngestionRunRepository(db_pool),
    )


@pytest.fixture
async def fake_kb(
    db_pool: AsyncConnectionPool[AsyncConnection],
    tmp_path: Path,
) -> AsyncGenerator[DocumentRepository]:
    """Like `seeded_kb`, but with `FakeEmbeddings` (no network call). For tests that
    exercise storage/SQL correctness (hash tracking, cascades, replace/remove) and
    don't assert on embedding semantics or ranking quality — use `seeded_kb` for those.
    """
    repository = DocumentRepository(
        db_pool, FakeEmbeddings(), summary_weight=RetrievalConfig().SUMMARY_WEIGHT
    )
    await ingestion_service(repository, db_pool, tmp_path).ingest(
        load_directory(FIXTURE_KB), remove_missing=False
    )
    yield repository
    async with db_pool.connection() as conn:
        # Cascades to their chunks.
        await conn.execute("DELETE FROM documents WHERE source_id LIKE 'it-%'")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seeded_kb(
    integration_settings: Settings,
    tmp_path_factory: pytest.TempPathFactory,
) -> AsyncGenerator[DocumentRepository]:
    """Ingests the small fixture knowledge base (source ids `it-*`, with facts that
    exist nowhere else, so a real knowledge base in the same database can't outrank
    it), once per test session, with real embeddings. `remove_missing=False` leaves
    any real knowledge base in the same database alone.

    Read-only by convention: shared across the whole session, so a test using this
    fixture must not mutate the KB (use `fake_kb` instead if it needs to).
    """
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        repository = DocumentRepository(
            pool,
            build_embeddings(integration_settings),
            summary_weight=integration_settings.RETRIEVAL.SUMMARY_WEIGHT,
        )
        await ingestion_service(
            repository, pool, tmp_path_factory.mktemp("seeded_kb")
        ).ingest(load_directory(FIXTURE_KB), remove_missing=False)
        yield repository
        async with pool.connection() as conn:
            # Cascades to their chunks.
            await conn.execute("DELETE FROM documents WHERE source_id LIKE 'it-%'")
