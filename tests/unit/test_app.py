import asyncio
import io
import json
import uuid
import zipfile
from collections.abc import Callable, Generator
from datetime import timedelta
from typing import Any, cast

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rag.adapters.jwt_codec import JwtTokenCodec
from rag.api.deps import get_current_user
from rag.app import create_app
from rag.config import (
    AuthConfig,
    LoggingObservabilityConfig,
    OpenAILLMConfig,
    Settings,
)
from rag.container import Container
from rag.domain.errors import DocumentNotFoundError
from rag.domain.models import (
    Chunk,
    SourceArtifact,
    ToolCall,
)
from rag.services.auth_service.service import AuthService
from rag.services.chat_service.service import ChatService
from rag.services.conversation_service.service import ConversationService
from rag.services.share_service.service import ShareService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.service import RetrievalService
from tests.unit.fakes import (
    FakeArchiveStore,
    FakeConversationRepository,
    FakeShareRepository,
    FakeDocumentIndex,
    FakeIngestionRunRepository,
    FakePasswordHasher,
    FakeUserRepository,
    StubAgent,
    StubGeneration,
)

_TEST_EMAIL = "test@example.com"
_TEST_PASSWORD = "correct horse battery staple"
_OTHER_EMAIL = "other@example.com"
_ADMIN_EMAIL = "admin@example.com"


class _StubRetrievalService:
    top_k = 3

    async def search(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        return [(Chunk(text="stub chunk", metadata={}), 1.0)]

    async def get_document(self, source_id: str) -> Chunk:
        if source_id == "missing":
            raise DocumentNotFoundError(source_id)
        return Chunk(text=f"content for {source_id}", metadata={})

    async def ping(self) -> None:
        return None


def _stub_settings() -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue] — unit tests must be hermetic, independent of the developer's .env
        LLM=OpenAILLMConfig(API_KEY=SecretStr("test-key"), MODEL="gpt-4o-mini"),
        DATABASE_URL=SecretStr("unused"),
        AUTH=AuthConfig(
            JWT_SECRET=SecretStr("test-secret-that-is-long-enough-32b"),
        ),
        OBSERVABILITY=LoggingObservabilityConfig(),
    )


def _build_auth_service() -> AuthService:
    return AuthService(
        user_repository=FakeUserRepository(),
        pass_hasher=FakePasswordHasher(),
        token_codec=JwtTokenCodec("test-secret-that-is-long-enough-32b", "HS256"),
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


@pytest.fixture
def client() -> Generator[TestClient]:
    auth_service = _build_auth_service()
    asyncio.run(auth_service.create_user(_TEST_EMAIL, _TEST_PASSWORD))
    asyncio.run(auth_service.create_user(_OTHER_EMAIL, _TEST_PASSWORD))
    asyncio.run(auth_service.create_user(_ADMIN_EMAIL, _TEST_PASSWORD, is_admin=True))

    conversation_repository = FakeConversationRepository()
    generation = StubGeneration("Greeting")
    agent = StubAgent(
        extra_events=[
            ToolCall(name="search", status="pending", query="hi"),
            ToolCall(name="search", status="done", output="stub result"),
        ],
        artifacts=[SourceArtifact(id="doc-a"), SourceArtifact(id="doc-b")],
    )
    container = Container(
        retrieval_service=cast(RetrievalService, _StubRetrievalService()),
        ingestion_service=IngestionService(
            FakeDocumentIndex(),
            WholeDocumentChunker(),
            FakeArchiveStore(),
            FakeIngestionRunRepository(),
        ),
        auth_service=auth_service,
        conversation_service=ConversationService(
            repository=conversation_repository,
            llm=generation,
        ),
        chat_service=ChatService(repository=conversation_repository, agent=agent),
        share_service=ShareService(
            shares=FakeShareRepository(conversation_repository),
            conversations=conversation_repository,
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


def test_ready_endpoint_exercises_retrieval_service(client: TestClient) -> None:
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
    assert body["top_k"] == 3  # the search's


def test_settings_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 401


def test_retrieval_endpoint_returns_document(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/retrieval/some-doc", headers=auth_headers)
    assert response.status_code == 200
    assert response.text == "content for some-doc"


def test_retrieval_endpoint_404_when_document_missing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/retrieval/missing", headers=auth_headers)
    assert response.status_code == 404


def test_retrieval_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/retrieval/some-doc")
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


def _parse_sse(body: str) -> list[dict]:
    """Each SSE event's `data`, JSON-parsed, mirroring how @microsoft/fetch-event-source
    (lib/cjs/parse.js) hands events to frontend/src/api/chat.ts's onmessage, which
    JSON-parses them: a blank line ends an event, repeated `data:` lines are joined
    with "\\n", one space after the colon is dropped, and comment lines are skipped.
    """
    events = []
    for block in filter(None, body.split("\n\n")):
        fields = [line.partition(":")[::2] for line in block.split("\n")]
        data = "\n".join(v.removeprefix(" ") for name, v in fields if name == "data")
        if data:
            events.append(json.loads(data))
    return events


def _create_conversation(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/api/conversations", headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


def _send(
    client: TestClient, headers: dict[str, str], conversation_id: str, message: str
) -> str:
    """Posts a message and returns the whole SSE body of its answer."""
    with client.stream(
        "POST",
        f"/api/chat/{conversation_id}",
        json={"message": message},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        return "".join(response.iter_text())


def _start_conversation(
    client: TestClient, headers: dict[str, str], message: str = "hi"
) -> str:
    """What the UI does for a first message: create, name it, then stream the answer."""
    conversation_id = _create_conversation(client, headers)
    response = client.post(
        f"/api/conversations/{conversation_id}/title",
        json={"message": message},
        headers=headers,
    )
    assert response.status_code == 200
    _send(client, headers, conversation_id, message)
    return conversation_id


def test_create_conversation_starts_it_untitled_and_empty(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/api/conversations", headers=auth_headers)

    assert response.status_code == 200
    conversation = response.json()
    assert set(conversation) == {
        "id",
        "title",
        "created_at",
        "updated_at",
        "pinned_at",
    }
    assert conversation["title"] is None
    assert conversation["pinned_at"] is None
    messages_url = f"/api/conversations/{conversation['id']}/messages"
    assert client.get(messages_url, headers=auth_headers).json() == []


def test_send_message_streams_the_answer(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    body = _send(client, auth_headers, _create_conversation(client, auth_headers), "hi")

    assert {"type": "text", "text": "echo: hi"} in _parse_sse(body)


def test_send_message_contract_matches_frontend_parsing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Locks the wire format to what frontend/src/api/chat.ts parses: one JSON object
    per event's `data`, told apart by `type`. The payloads' fields are typed through
    OpenAPI (TextEvent/ToolEvent/ArtifactsEvent); this checks they arrive that way.
    """
    conversation_id = _create_conversation(client, auth_headers)

    events = _parse_sse(_send(client, auth_headers, conversation_id, "hi"))

    assert events == [
        {"type": "text", "text": "echo: hi"},
        {
            "type": "tool",
            "name": "search",
            "status": "pending",
            "query": "hi",
            "output": None,
        },
        {
            "type": "tool",
            "name": "search",
            "status": "done",
            "query": None,
            "output": "stub result",
        },
        {
            "type": "artifacts",
            "artifacts": [
                {"kind": "source", "id": "doc-a"},
                {"kind": "source", "id": "doc-b"},
            ],
        },
    ]


def test_send_message_text_with_newlines_survives_sse_framing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """LLM tokens are full of "\\n" (markdown); a raw "\\n\\n" in a data field would end
    the SSE event early and drop the text after it.
    """
    message = "# Title\n\n- item\n- item"
    conversation_id = _create_conversation(client, auth_headers)

    body = _send(client, auth_headers, conversation_id, message)

    text_events = [e for e in _parse_sse(body) if e["type"] == "text"]
    assert text_events == [{"type": "text", "text": f"echo: {message}"}]


def test_the_agent_gets_the_message_normalized(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _create_conversation(client, auth_headers)

    body = _send(client, auth_headers, conversation_id, "  ｈｉ\u200b\U000e0041 ")

    assert {"type": "text", "text": "echo: hi"} in _parse_sse(body)


def test_generate_title_renames_the_conversation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers)

    response = client.post(
        f"/api/conversations/{conversation_id}/title",
        json={"message": "hi"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Greeting"
    listed = client.get("/api/conversations", headers=auth_headers).json()
    assert listed["items"][0]["title"] == "Greeting"


def test_send_message_404s_for_a_conversation_the_user_does_not_own(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _create_conversation(client, _login(client, _OTHER_EMAIL))

    response = client.post(
        f"/api/chat/{conversation_id}",
        json={"message": "hijack"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


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
    assert page1["items"][0]["title"] == "Greeting"  # named from its first message
    assert page2["next_cursor"] is None


def test_pinning_moves_a_conversation_from_the_list_to_the_pinned_ones(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _start_conversation(client, auth_headers, "first")
    second = _start_conversation(client, auth_headers, "second")

    response = client.patch(
        f"/api/conversations/{first}", json={"pinned": True}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["pinned_at"] is not None
    pinned = client.get("/api/conversations/pinned", headers=auth_headers).json()
    listed = client.get("/api/conversations", headers=auth_headers).json()
    assert [c["id"] for c in pinned] == [first]
    assert [c["id"] for c in listed["items"]] == [second]


def test_rename_stores_the_title_on_one_line(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers)

    response = client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "  Billing\n  questions "},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Billing questions"
    listed = client.get("/api/conversations", headers=auth_headers).json()
    assert listed["items"][0]["title"] == "Billing questions"


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_rename_rejects_a_blank_or_too_long_title(
    client: TestClient, auth_headers: dict[str, str], title: str
) -> None:
    conversation_id = _start_conversation(client, auth_headers)

    response = client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": title},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_404s_for_a_conversation_the_user_does_not_own(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _create_conversation(client, _login(client, _OTHER_EMAIL))

    response = client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "mine now", "pinned": True},
        headers=auth_headers,
    )

    assert response.status_code == 404


def _share(client: TestClient, headers: dict[str, str], conversation_id: str):
    return client.put(f"/api/conversations/{conversation_id}/share", headers=headers)


def _questions(shared: dict[str, Any]) -> list[str]:
    return [m["text"] for m in shared["messages"] if m["role"] == "user"]


def test_a_shared_conversation_is_readable_without_signing_in(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers, "hi")

    share = _share(client, auth_headers, conversation_id)

    assert share.status_code == 200
    assert share.json()["title"] == "Greeting"
    shared = client.get(f"/api/shares/{share.json()['id']}")  # no auth headers
    assert shared.status_code == 200
    body = shared.json()
    assert body["title"] == "Greeting"
    assert body["messages"][0] == {"role": "user", "text": "hi"}
    assert body["messages"][1]["role"] == "assistant"


def test_a_share_is_a_snapshot_until_shared_again(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers, "hi")
    share_id = _share(client, auth_headers, conversation_id).json()["id"]

    _send(client, auth_headers, conversation_id, "later")
    before = client.get(f"/api/shares/{share_id}").json()
    again = _share(client, auth_headers, conversation_id).json()
    after = client.get(f"/api/shares/{share_id}").json()

    assert _questions(before) == ["hi"]
    assert again["id"] == share_id  # same link, new snapshot
    assert _questions(after) == ["hi", "later"]


def test_get_share_is_null_until_shared_and_after_unsharing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers)
    url = f"/api/conversations/{conversation_id}/share"
    assert client.get(url, headers=auth_headers).json() is None

    share_id = _share(client, auth_headers, conversation_id).json()["id"]
    assert client.get(url, headers=auth_headers).json()["id"] == share_id

    assert client.delete(url, headers=auth_headers).status_code == 204
    assert client.get(url, headers=auth_headers).json() is None
    assert client.get(f"/api/shares/{share_id}").status_code == 404


def test_deleting_a_conversation_takes_its_link_down(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _start_conversation(client, auth_headers)
    share_id = _share(client, auth_headers, conversation_id).json()["id"]

    client.delete(f"/api/conversations/{conversation_id}", headers=auth_headers)

    assert client.get(f"/api/shares/{share_id}").status_code == 404


def test_an_empty_conversation_cannot_be_shared(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    conversation_id = _create_conversation(client, auth_headers)

    assert _share(client, auth_headers, conversation_id).status_code == 409


def test_only_the_owner_can_share_or_unshare(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    other = _login(client, _OTHER_EMAIL)
    conversation_id = _start_conversation(client, other)
    url = f"/api/conversations/{conversation_id}/share"

    assert client.put(url, headers=auth_headers).status_code == 404
    assert client.get(url, headers=auth_headers).status_code == 404
    assert client.delete(url, headers=auth_headers).status_code == 404


def test_an_unknown_share_link_is_not_found(client: TestClient) -> None:
    assert client.get(f"/api/shares/{uuid.uuid4()}").status_code == 404


def test_a_message_moves_a_conversation_to_the_top_of_the_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _start_conversation(client, auth_headers, "first")
    second = _start_conversation(client, auth_headers, "second")

    _send(client, auth_headers, first, "again")

    listed = client.get("/api/conversations", headers=auth_headers).json()
    assert [c["id"] for c in listed["items"]] == [first, second]


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

    # The answer as the same events its stream sent, for the frontend to replay.
    assert client.get(messages_url, headers=auth_headers).json() == [
        {"role": "user", "text": "hi"},
        {
            "role": "assistant",
            "events": [
                {"type": "text", "text": "echo: hi"},
                {
                    "type": "tool",
                    "name": "search",
                    "status": "pending",
                    "query": "hi",
                    "output": None,
                },
                {
                    "type": "tool",
                    "name": "search",
                    "status": "done",
                    "query": None,
                    "output": "stub result",
                },
                {
                    "type": "artifacts",
                    "artifacts": [
                        {"kind": "source", "id": "doc-a"},
                        {"kind": "source", "id": "doc-b"},
                    ],
                },
            ],
        },
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
        ("POST", "/api/conversations"),
        ("GET", f"/api/conversations/{uuid.uuid4()}/messages"),
        ("POST", f"/api/chat/{uuid.uuid4()}"),
        ("POST", f"/api/conversations/{uuid.uuid4()}/title"),
        ("DELETE", f"/api/conversations/{uuid.uuid4()}"),
    ],
)
def test_conversation_endpoints_require_auth(
    client: TestClient, method: str, path: str
) -> None:
    assert client.request(method, path).status_code == 401


# Routes anyone may call. Every other route must require a signed-in user.
_PUBLIC_ROUTES = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/health/live"),
    ("GET", "/api/health/ready"),
    ("GET", "/api/shares/{share_id}"),
}


def _dependency_calls(dependant: Dependant) -> set[Callable[..., object] | None]:
    """Every callable in a route's dependency tree, router-level dependencies included."""
    return {
        dependant.call,
        *(call for dep in dependant.dependencies for call in _dependency_calls(dep)),
    }


def test_every_route_requires_a_signed_in_user_unless_public() -> None:
    """A new route, or a whole router, that forgets its auth dependency fails here
    instead of shipping open. Admin routes count: get_current_admin depends on
    get_current_user. A public route that became protected fails too, so the list
    above can't go stale.
    """
    app = create_app(settings=_stub_settings())

    # iter_route_contexts gives each route with its router's settings applied, as the
    # OpenAPI schema sees it (app.routes only lists the included routers).
    unprotected = {
        (method, route.path)
        for route in iter_route_contexts(app.routes)
        if isinstance(route.original_route, APIRoute)
        and get_current_user not in _dependency_calls(route.dependant)
        for method in route.methods or ()
    }

    assert unprotected == _PUBLIC_ROUTES


def _kb_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("kb/a.md", "# A")
        archive.writestr("kb/b.md", "# B")
    return buffer.getvalue()


def _upload(client: TestClient, headers: dict[str, str], data: bytes):
    return client.post(
        "/api/ingestions",
        headers=headers,
        files={"file": ("kb.zip", data, "application/zip")},
    )


def test_admin_upload_runs_ingestion_in_the_background(client: TestClient) -> None:
    headers = _login(client, _ADMIN_EMAIL)
    assert client.get("/api/ingestions/latest", headers=headers).json() is None

    response = _upload(client, headers, _kb_zip())

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    # TestClient runs background tasks before returning, so the run has ended.
    run = client.get(f"/api/ingestions/{response.json()['id']}", headers=headers)
    assert run.json()["status"] == "succeeded"
    assert run.json()["added"] == 2
    latest = client.get("/api/ingestions/latest", headers=headers)
    assert latest.json()["id"] == response.json()["id"]


def test_upload_rejects_an_invalid_zip(client: TestClient) -> None:
    response = _upload(client, _login(client, _ADMIN_EMAIL), b"not a zip")

    assert response.status_code == 400
    assert "not a zip file" in response.json()["detail"]


def test_ingestions_are_admin_only(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert _upload(client, auth_headers, _kb_zip()).status_code == 403
    assert client.get("/api/ingestions/latest", headers=auth_headers).status_code == 403
    assert client.get("/api/ingestions/latest").status_code == 401


def test_unknown_ingestion_run_is_404(client: TestClient) -> None:
    response = client.get(
        f"/api/ingestions/{uuid.uuid4()}", headers=_login(client, _ADMIN_EMAIL)
    )
    assert response.status_code == 404
