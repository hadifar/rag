import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from pydantic import ValidationError

from rag.adapters.llm_client import build_embeddings
from rag.config import Settings
from rag.repository.document_repository import DocumentRepository
from rag.services.ingestion_service.chunking import MarkdownHeaderChunker
from rag.services.ingestion_service.loaders import MarkdownFileLoader
from rag.services.ingestion_service.service import IngestionService

FIXTURE_KB = Path(__file__).parent / "fixtures" / "kb"


@pytest.fixture(scope="module")
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


@pytest.fixture
async def seeded_kb(
    integration_settings: Settings, db_pool: AsyncConnectionPool[AsyncConnection]
) -> AsyncGenerator[DocumentRepository]:
    """Ingests the small fixture knowledge base (source ids `it-*`, with facts that
    exist nowhere else, so a real knowledge base in the same database can't outrank
    it), and removes it afterwards. Uses real embeddings. `remove_missing=False` leaves
    any real knowledge base in the same database alone.
    """
    repository = DocumentRepository(db_pool, build_embeddings(integration_settings))
    await IngestionService(repository, MarkdownHeaderChunker()).ingest(
        MarkdownFileLoader(FIXTURE_KB), remove_missing=False
    )
    yield repository
    async with db_pool.connection() as conn:
        # Cascades to their chunks.
        await conn.execute("DELETE FROM documents WHERE source_id LIKE 'it-%'")
