import pytest
from pydantic import ValidationError

from rag.config import Settings


@pytest.fixture(scope="module")
def integration_settings() -> Settings:
    """Real Settings loaded from .env — points at the same Pinecone indexes/namespace
    `rag ingest` populates, so tests query the actual knowledge base, read-only.
    """
    try:
        return Settings()  # pyright: ignore[reportCallIssue] — fields come from .env
    except ValidationError as exc:
        pytest.skip(f"Pinecone/OpenAI credentials not configured in .env: {exc}")
