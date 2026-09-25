import json
from collections.abc import AsyncIterator, Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from pydantic import SecretStr

from rag.api.routers.chat import SseEventType
from rag.app import create_app
from rag.config import LoggingObservability, OpenAILLM, Settings
from rag.container import Container
from rag.domain.events import (
    SourcesReady,
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)
from rag.services.generation_service.service import GenerationService
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
        yield ToolCallStart(name="search", query=message)
        yield ToolCallResult(name="search", output="stub result")
        yield SourcesReady(sources=["doc-a", "doc-b"])


def _stub_settings() -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue] — unit tests must be hermetic, independent of the developer's .env
        LLM=OpenAILLM(API_KEY=SecretStr("test-key"), MODEL="gpt-4o-mini"),
        PINECONE_API_KEY=SecretStr("test-key"),
        PINECONE_DENSE_INDEX_NAME="dense",
        PINECONE_SPARSE_INDEX_NAME="sparse",
        PINECONE_CLOUD="aws",
        PINECONE_REGION="us-east-1",
        PINECONE_DENSE_MODEL="dense-model",
        PINECONE_SPARSE_MODEL="sparse-model",
        PINECONE_NAMESPACE="ns",
        OBSERVABILITY=LoggingObservability(),
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


def _parse_sse(body: str) -> list[tuple[str, str]]:
    """Splits an SSE body into (event, data) pairs, mirroring how
    @microsoft/fetch-event-source hands events to frontend/src/api/chat.ts's onmessage.
    """
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], lines["data"]))
    return events


def test_chat_stream_endpoint_wired(client: TestClient) -> None:
    with client.stream(
        "POST", "/api/chat/stream", json={"message": "hi", "thread_id": "t1"}
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: text" in body
    assert "echo: hi" in body


def test_chat_stream_contract_matches_frontend_parsing(client: TestClient) -> None:
    """Locks the SSE wire format to what frontend/src/api/chat.ts actually parses.

    This endpoint returns raw text/event-stream, so it's invisible to the OpenAPI
    schema (and therefore to openapi-typescript) — this test is the only thing
    that catches a field rename here before it breaks the frontend at runtime.
    """
    with client.stream(
        "POST", "/api/chat/stream", json={"message": "hi", "thread_id": "t1"}
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    events = _parse_sse(body)
    assert [event for event, _ in events] == [
        SseEventType.TEXT,
        SseEventType.TOOL_START,
        SseEventType.TOOL_RESULT,
        SseEventType.SOURCES,
    ]

    text_event, tool_start_event, tool_result_event, sources_event = events

    # frontend: onEvent({ type: 'text', text: ev.data }) — raw, unparsed data.
    assert text_event[1] == "echo: hi"

    # frontend: const { name, query } = JSON.parse(ev.data)
    assert json.loads(tool_start_event[1]) == {
        "name": "search",
        "query": "hi",
    }

    # frontend: const { name, output } = JSON.parse(ev.data)
    assert json.loads(tool_result_event[1]) == {
        "name": "search",
        "output": "stub result",
    }

    # frontend: const { names } = JSON.parse(ev.data)
    assert json.loads(sources_event[1]) == {"names": ["doc-a", "doc-b"]}
