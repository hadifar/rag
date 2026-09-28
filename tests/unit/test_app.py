import asyncio
import json
import uuid
from collections.abc import Generator
from datetime import timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from pydantic import SecretStr

from rag.api.routers.chat import SseEventType
from rag.app import create_app
from rag.config import (
    AuthConfig,
    LoggingObservability,
    OpenAILLM,
    Settings,
)
from rag.container import Container
from rag.domain.events import SourcesReady, ToolCallResult, ToolCallStart
from rag.services.auth_service.service import AuthService
from rag.services.conversation_service.service import ConversationService
from rag.services.generation_service.service import GenerationService
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.service import RetrievalService
from tests.unit.fakes import (
    FakeConversationRepository,
    FakeTitleModel,
    FakeUserRepository,
    StubChatEngine,
)

_TEST_EMAIL = "test@example.com"
_TEST_PASSWORD = "correct horse battery staple"
_OTHER_EMAIL = "other@example.com"


class _StubRetrievalService:
    async def search(self, query: str, top_k: int = 3) -> list[tuple[Document, float]]:
        return [(Document(page_content="stub chunk", metadata={}), 1.0)]

    async def get_document(self, source_id: str) -> Document | None:
        if source_id == "missing":
            return None
        return Document(page_content=f"content for {source_id}", metadata={})

    async def ping(self) -> None:
        return None


def _stub_settings() -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue] — unit tests must be hermetic, independent of the developer's .env
        LLM=OpenAILLM(API_KEY=SecretStr("test-key"), MODEL="gpt-4o-mini"),
        DATABASE_URL=SecretStr("unused"),
        AUTH=AuthConfig(
            JWT_SECRET=SecretStr("test-secret-that-is-long-enough-32b"),
        ),
        OBSERVABILITY=LoggingObservability(),
    )


def _build_auth_service() -> AuthService:
    return AuthService(
        user_repository=FakeUserRepository(),
        jwt_secret="test-secret-that-is-long-enough-32b",
        jwt_algorithm="HS256",
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


@pytest.fixture
def client() -> Generator[TestClient]:
    auth_service = _build_auth_service()
    asyncio.run(auth_service.create_user(_TEST_EMAIL, _TEST_PASSWORD))
    asyncio.run(auth_service.create_user(_OTHER_EMAIL, _TEST_PASSWORD))

    chat_engine = StubChatEngine(
        extra_events=[
            ToolCallStart(name="search", query="hi"),
            ToolCallResult(name="search", output="stub result"),
            SourcesReady(sources=["doc-a", "doc-b"]),
        ]
    )
    container = Container(
        ranking_service=cast(RetrievalService, _StubRetrievalService()),
        generation_service=cast(GenerationService, chat_engine),
        ingestion_service=cast(IngestionService, object()),
        auth_service=auth_service,
        conversation_service=ConversationService(
            repository=FakeConversationRepository(),
            chat_engine=chat_engine,
            title_model=cast(Runnable, FakeTitleModel(reply="Greeting")),
        ),
    )
    app = create_app(container=container, settings=_stub_settings())
    # https, so the client sends the (always Secure) refresh cookie back.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": _TEST_PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    return _login(client, _TEST_EMAIL)


def test_live_endpoint_ok(client: TestClient) -> None:
    response = client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_exercises_ranking_service(client: TestClient) -> None:
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_endpoint_returns_config(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/settings", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "gpt-4o-mini"
    assert body["temperature"] == 0.2
    assert body["top_k"] == 4


def test_settings_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 401


def test_kb_endpoint_returns_document(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/kb/some-doc", headers=auth_headers)
    assert response.status_code == 200
    assert response.text == "content for some-doc"


def test_kb_endpoint_404_when_document_missing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/kb/missing", headers=auth_headers)
    assert response.status_code == 404


def test_kb_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/kb/some-doc")
    assert response.status_code == 401


def test_login_wrong_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": _TEST_EMAIL, "password": "wrong"}
    )
    assert response.status_code == 401


def test_me_endpoint_returns_current_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == _TEST_EMAIL
    assert response.json()["is_admin"] is False


def test_refresh_endpoint_issues_new_access_token(client: TestClient) -> None:
    login_response = client.post(
        "/api/auth/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD}
    )
    assert login_response.status_code == 200

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


def test_login_sets_secure_refresh_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD}
    )
    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"].lower()
    assert set_cookie.startswith("refresh_token=")
    assert "; secure" in set_cookie
    assert "; httponly" in set_cookie


def test_refresh_without_cookie_rejected(client: TestClient) -> None:
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401


def test_logout_clears_refresh_cookie(client: TestClient) -> None:
    login_response = client.post(
        "/api/auth/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD}
    )
    assert login_response.status_code == 200

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 401


def _parse_sse(body: str) -> list[tuple[str, str]]:
    """Splits an SSE body into (event, data) pairs, mirroring how
    @microsoft/fetch-event-source (lib/cjs/parse.js) hands events to
    frontend/src/api/chat.ts's onmessage: a blank line ends an event, repeated
    `data:` lines are joined with "\\n", and one space after the colon is dropped.
    """
    events = []
    for block in filter(None, body.split("\n\n")):
        fields = [line.partition(":")[::2] for line in block.split("\n")]
        values = [(name, value.removeprefix(" ")) for name, value in fields]
        event = next((value for name, value in values if name == "event"), "")
        data = "\n".join(value for name, value in values if name == "data")
        events.append((event, data))
    return events


def test_chat_stream_endpoint_requires_auth(client: TestClient) -> None:
    response = client.post("/api/chat/stream", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_stream_endpoint_wired(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "hi"},
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: text" in body
    assert "echo: hi" in body


def test_chat_stream_contract_matches_frontend_parsing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Locks the SSE wire format to what frontend/src/api/chat.ts actually parses.

    This endpoint returns raw text/event-stream, so it's invisible to the OpenAPI
    schema (and therefore to openapi-typescript) — this test is the only thing
    that catches a field rename here before it breaks the frontend at runtime.
    """
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "hi"},
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    events = _parse_sse(body)
    assert [event for event, _ in events] == [
        SseEventType.CONVERSATION,
        SseEventType.TEXT,
        SseEventType.TOOL_START,
        SseEventType.TOOL_RESULT,
        SseEventType.SOURCES,
        SseEventType.TITLE,
    ]

    (
        conversation_event,
        text_event,
        tool_start_event,
        tool_result_event,
        sources_event,
        title_event,
    ) = events

    # frontend: const conversation = JSON.parse(ev.data) as Schemas['ConversationResponse']
    conversation = json.loads(conversation_event[1])
    assert set(conversation) == {"id", "title", "created_at", "updated_at"}
    assert conversation["title"] == "hi"  # fallback until the generated title arrives

    # frontend: const { text } = JSON.parse(ev.data)
    assert json.loads(text_event[1]) == {"text": "echo: hi"}

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
    assert json.loads(sources_event[1]) == {"sources": ["doc-a", "doc-b"]}

    # frontend: const { id, title } = JSON.parse(ev.data)
    assert json.loads(title_event[1]) == {"id": conversation["id"], "title": "Greeting"}


def test_chat_stream_text_with_newlines_survives_sse_framing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """LLM tokens are full of "\\n" (markdown); a raw "\\n\\n" in a data field would end
    the SSE event early and drop the text after it.
    """
    message = "# Title\n\n- item\r\n- item\n"
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": message},
        headers=auth_headers,
    ) as response:
        body = "".join(response.iter_text())

    text_events = [data for event, data in _parse_sse(body) if event == "text"]
    assert [json.loads(data) for data in text_events] == [{"text": f"echo: {message}"}]


def _start_conversation(
    client: TestClient, headers: dict[str, str], message: str = "hi"
) -> str:
    with client.stream(
        "POST", "/api/chat/stream", json={"message": message}, headers=headers
    ) as response:
        body = "".join(response.iter_text())
    events = dict(_parse_sse(body))
    return json.loads(events[SseEventType.CONVERSATION])["id"]


def test_chat_stream_continues_an_existing_conversation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "again", "conversation_id": conversation_id},
        headers=auth_headers,
    ) as response:
        body = "".join(response.iter_text())

    events = dict(_parse_sse(body))
    assert json.loads(events[SseEventType.CONVERSATION])["id"] == conversation_id
    assert SseEventType.TITLE not in events  # only a new conversation gets titled


def test_chat_stream_404s_for_a_conversation_the_user_does_not_own(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, _login(client, _OTHER_EMAIL))

    response = client.post(
        "/api/chat/stream",
        json={"message": "hijack", "conversation_id": conversation_id},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_chat_stream_creates_a_new_conversation_under_the_clients_id(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client_id = str(uuid.uuid4())

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "hi", "conversation_id": client_id},
        headers=auth_headers,
    ) as response:
        body = "".join(response.iter_text())

    events = dict(_parse_sse(body))
    assert json.loads(events[SseEventType.CONVERSATION])["id"] == client_id
    history = client.get(
        f"/api/conversations/{client_id}/messages", headers=auth_headers
    )
    assert history.status_code == 200


def test_conversations_list_is_newest_first_and_paginated(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _start_conversation(client, auth_headers, "first")
    second = _start_conversation(client, auth_headers, "second")
    _start_conversation(client, _login(client, _OTHER_EMAIL), "not mine")

    page1 = client.get("/api/conversations?limit=1", headers=auth_headers).json()
    page2 = client.get(
        "/api/conversations",
        params={"limit": 1, "cursor": page1["next_cursor"]},
        headers=auth_headers,
    ).json()

    assert [c["id"] for c in page1["items"] + page2["items"]] == [second, first]
    assert page1["items"][0]["title"] == "Greeting"
    assert page2["next_cursor"] is None


@pytest.mark.parametrize(
    ("query", "status"), [("cursor=garbage", 400), ("limit=0", 422), ("limit=101", 422)]
)
def test_conversations_list_rejects_bad_parameters(
    client: TestClient, auth_headers: dict[str, str], query: str, status: int
) -> None:
    response = client.get(f"/api/conversations?{query}", headers=auth_headers)
    assert response.status_code == status


def test_conversation_messages_and_delete(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers)
    messages_url = f"/api/conversations/{conversation_id}/messages"

    messages = client.get(messages_url, headers=auth_headers).json()
    assert [(m["role"], m["text"]) for m in messages] == [
        ("user", "hi"),
        ("assistant", "echo: hi"),
    ]

    deleted = client.delete(
        f"/api/conversations/{conversation_id}", headers=auth_headers
    )
    assert deleted.status_code == 204
    assert client.get(messages_url, headers=auth_headers).status_code == 404
    listed = client.get("/api/conversations", headers=auth_headers).json()
    assert listed["items"] == []


def test_conversations_of_another_user_are_invisible(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    others = _start_conversation(client, _login(client, _OTHER_EMAIL))

    assert (
        client.get(
            f"/api/conversations/{others}/messages", headers=auth_headers
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/conversations/{others}", headers=auth_headers).status_code
        == 404
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/conversations"),
        ("GET", f"/api/conversations/{uuid.uuid4()}/messages"),
        ("DELETE", f"/api/conversations/{uuid.uuid4()}"),
    ],
)
def test_conversation_endpoints_require_auth(
    client: TestClient, method: str, path: str
) -> None:
    assert client.request(method, path).status_code == 401
