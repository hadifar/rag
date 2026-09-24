from collections.abc import AsyncIterator, Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from pydantic import SecretStr

from rag.app import create_app
from rag.config import Settings
from rag.container import Container
from rag.services.generation_service.service import GenerationService
from rag.services.generation_service.streaming import StreamEvent, TextDelta
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.service import RetrievalService


class _StubRetrievalService:
    async def search(self, query: str, top_k: int = 3) -> list[tuple[Document, float]]:
        return [(Document(page_content="stub chunk", metadata={}), 1.0)]

    async def get_document(self, source_id: str) -> Document | None:
        if source_id == "missing":
            return None
        return Document(page_content=f"content for {source_id}", metadata={})


class _StubGenerationService:
    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        yield TextDelta(text=f"echo: {message}")


def _stub_settings() -> Settings:
    return Settings(
        OPENAI_API_KEY=SecretStr("test-key"),
        OPENAI_MODEL="gpt-4o-mini",
        PINECONE_API_KEY=SecretStr("test-key"),
        PINECONE_DENSE_INDEX_NAME="dense",
        PINECONE_SPARSE_INDEX_NAME="sparse",
        PINECONE_CLOUD="aws",
        PINECONE_REGION="us-east-1",
        PINECONE_DENSE_MODEL="dense-model",
        PINECONE_SPARSE_MODEL="sparse-model",
        PINECONE_NAMESPACE="ns",
        LANGFUSE_PUBLIC_KEY=SecretStr("pk"),
        LANGFUSE_SECRET_KEY=SecretStr("sk"),
        LANGFUSE_HOST="http://localhost",
        OBSERVABILITY_BACKEND="logging",
    )


@pytest.fixture
def client() -> Generator[TestClient]:
    container = Container(
        ranking_service=cast(RetrievalService, _StubRetrievalService()),
        generation_service=cast(GenerationService, _StubGenerationService()),
        ingestion_service=cast(IngestionService, object()),
    )
    app = create_app(container=container, settings=_stub_settings())
    with TestClient(app) as test_client:
        yield test_client


def test_live_endpoint_ok(client: TestClient) -> None:
    response = client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_exercises_ranking_service(client: TestClient) -> None:
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_endpoint_returns_config(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "gpt-4o-mini"
    assert body["temperature"] == 0.2
    assert body["top_k"] == 4


def test_kb_endpoint_returns_document(client: TestClient) -> None:
    response = client.get("/api/kb/some-doc")
    assert response.status_code == 200
    assert response.text == "content for some-doc"


def test_kb_endpoint_404_when_document_missing(client: TestClient) -> None:
    response = client.get("/api/kb/missing")
    assert response.status_code == 404


def test_chat_stream_endpoint_wired(client: TestClient) -> None:
    with client.stream(
        "POST", "/api/chat/stream", json={"message": "hi", "thread_id": "t1"}
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: text" in body
    assert "echo: hi" in body
