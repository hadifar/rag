import hashlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from rag.domain.errors import IngestionInProgressError
from rag.domain.models import (
    AgentSpec,
    Conversation,
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    Preference,
    ReferencesReady,
    RunContext,
    StreamEvent,
    TextDelta,
    Turn,
    User,
)
from rag.domain.ports import ChatAgentPort


class FakeEmbeddings:
    """Deterministic EmbeddingsPort: same text -> same vector, instant, no network.

    Vectors are NOT semantically meaningful — only use where a test needs *a*
    vector to satisfy storage, not one that reflects real similarity.
    """

    DIMENSIONS = 1536

    async def aembed_query(self, text: str) -> list[float]:
        return self._vector(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        raw = (seed * (self.DIMENSIONS // len(seed) + 1))[: self.DIMENSIONS]
        return [(b / 127.5) - 1 for b in raw]


class FakePasswordHasher:
    """PasswordHasherPort without the cost: Argon2 is slow on purpose (~70 ms a hash),
    which every API test would pay in its fixture. The real one is tested in
    test_auth_service.py.
    """

    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, hashed_password: str, password: str) -> bool:
        return hashed_password == f"hashed:{password}"


class FakeUserRepository:
    """In-memory UserRepositoryPort."""

    def __init__(self):
        self._users: dict[uuid.UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(user_id)

    async def create(
        self, email: str, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.now(UTC),
            is_admin=is_admin,
        )
        self._users[user.id] = user
        return user

    async def set_admin(self, email: str, is_admin: bool) -> User | None:
        user = await self.get_by_email(email)
        if user is None:
            return None
        self._users[user.id] = replace(user, is_admin=is_admin)
        return self._users[user.id]


class FakeIngestionRunRepository:
    """In-memory IngestionRunRepositoryPort, one running run at a time like the real one."""

    def __init__(self):
        self.runs: dict[uuid.UUID, IngestionRun] = {}
        self._clock = datetime(2026, 1, 1, tzinfo=UTC)

    async def create(
        self, archive_name: str, created_by: uuid.UUID | None
    ) -> IngestionRun:
        if await self.running() is not None:
            raise IngestionInProgressError()
        self._clock += timedelta(seconds=1)
        run = IngestionRun(
            id=uuid.uuid4(),
            status="running",
            archive_name=archive_name,
            created_by=created_by,
            started_at=self._clock,
        )
        self.runs[run.id] = run
        return run

    async def get(self, run_id: uuid.UUID) -> IngestionRun | None:
        return self.runs.get(run_id)

    async def latest(self) -> IngestionRun | None:
        return max(self.runs.values(), key=lambda r: r.started_at, default=None)

    async def running(self) -> IngestionRun | None:
        return next((r for r in self.runs.values() if r.status == "running"), None)

    async def finish(self, run_id: uuid.UUID, report: IngestionReport) -> None:
        self.runs[run_id] = replace(
            self.runs[run_id], status="succeeded", **asdict(report)
        )

    async def fail(self, run_id: uuid.UUID, error: str) -> None:
        self.runs[run_id] = replace(self.runs[run_id], status="failed", error=error)

    async def fail_running(self, error: str) -> int:
        running = [r for r in self.runs.values() if r.status == "running"]
        for run in running:
            await self.fail(run.id, error)
        return len(running)


class FakeArchiveStore:
    """In-memory ArchiveStorePort; names are sequential, so they sort like real ones."""

    def __init__(self):
        self.archives: dict[str, bytes] = {}

    async def asave(self, data: bytes) -> str:
        name = f"{len(self.archives):04d}.zip"
        self.archives[name] = data
        return name

    async def aread(self, name: str) -> bytes:
        return self.archives[name]

    async def alatest(self) -> str | None:
        return max(self.archives, default=None)


class FakeDocumentIndex:
    """In-memory DocumentIndexPort; records each replace call to assert on what was
    (re-)embedded.
    """

    def __init__(self, hashes: dict[str, str] | None = None):
        self.hashes = dict(hashes or {})
        self.replaced: list[tuple[list[IndexedDocument], list[str]]] = []

    async def alist_content_hashes(self) -> dict[str, str]:
        return dict(self.hashes)

    async def areplace_documents(
        self, documents: list[IndexedDocument], *, removed: list[str]
    ) -> None:
        self.replaced.append((documents, removed))
        for source_id in removed:
            del self.hashes[source_id]
        for document in documents:
            self.hashes[document.source_id] = document.content_hash


class FakeConversationRepository:
    """In-memory ConversationRepositoryPort. Each write advances a fake clock, so
    ordering by updated_at is deterministic without sleeping.
    """

    def __init__(self):
        self.rows: dict[uuid.UUID, Conversation] = {}
        self._clock = datetime(2026, 1, 1, tzinfo=UTC)

    def _now(self) -> datetime:
        self._clock += timedelta(seconds=1)
        return self._clock

    async def get_or_create_empty(self, user_id: uuid.UUID) -> Conversation:
        empty = next(
            (c for c in self.rows.values() if c.user_id == user_id and c.title is None),
            None,
        )
        if empty is not None:
            touched = await self.touch(empty.id)
            assert touched is not None
            return touched
        now = self._now()
        conversation = Conversation(
            id=uuid.uuid4(), user_id=user_id, title=None, created_at=now, updated_at=now
        )
        self.rows[conversation.id] = conversation
        return conversation

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self.rows.get(conversation_id)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        mine = sorted(
            (c for c in self.rows.values() if c.user_id == user_id),
            key=lambda c: (c.updated_at, c.id),
            reverse=True,
        )
        if before is not None:
            mine = [c for c in mine if (c.updated_at, c.id) < before]
        return mine[:limit]

    async def touch(self, conversation_id: uuid.UUID) -> Conversation | None:
        if conversation_id not in self.rows:
            return None
        self.rows[conversation_id] = replace(
            self.rows[conversation_id], updated_at=self._now()
        )
        return self.rows[conversation_id]

    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None:
        self.rows[conversation_id] = replace(self.rows[conversation_id], title=title)

    async def delete(self, conversation_id: uuid.UUID) -> None:
        self.rows.pop(conversation_id, None)


class StubGeneration:
    """AgentServicePort without agents: answers every prompt with `reply`, or raises
    `error`, and records the prompts.
    """

    def __init__(self, reply: str = "Generated title", error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.reply

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        # The reply, as the one field of the structured answer.
        return schema.model_validate({"title": await self.generate(prompt)})

    def create_agent(self, spec: AgentSpec) -> ChatAgentPort:
        raise NotImplementedError("the stub builds no agent")


class FakePreferenceRepository:
    """PreferenceRepositoryPort in memory: each user's preferences, oldest first."""

    def __init__(self):
        self.rows: dict[uuid.UUID, list[Preference]] = {}

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        return list(self.rows.get(user_id, []))

    async def add(self, user_id: uuid.UUID, preference: Preference) -> Preference:
        self.rows.setdefault(user_id, []).append(preference)
        return preference

    async def delete(self, user_id: uuid.UUID, preference_id: str) -> bool:
        kept = [p for p in self.rows.get(user_id, []) if p.id != preference_id]
        if len(kept) == len(self.rows.get(user_id, [])):
            return False
        self.rows[user_id] = kept
        return True


class FakeTranscriptRepository:
    """TranscriptRepositoryPort in memory: each conversation's turns, in order."""

    def __init__(self):
        self.turns: dict[uuid.UUID, list[Turn]] = {}

    async def append_turn(
        self, conversation_id: uuid.UUID, question: str, answer: list[StreamEvent]
    ) -> None:
        self.turns.setdefault(conversation_id, []).append(Turn(question, list(answer)))

    async def list_turns(self, conversation_id: uuid.UUID) -> list[Turn]:
        return list(self.turns.get(conversation_id, []))


class StubChatAgent:
    """ChatAgentPort without a model: echoes the message, then `extra_events`, then
    `references` if given; records the conversations it was told to forget.
    """

    def __init__(
        self,
        extra_events: list[StreamEvent] | None = None,
        references: list[str] | None = None,
    ):
        self.extra_events = extra_events or []
        self.references = references
        self.forgotten: list[uuid.UUID] = []

    async def stream(self, message: str, ctx: RunContext) -> AsyncIterator[StreamEvent]:
        yield TextDelta(text=f"echo: {message}")
        for event in self.extra_events:
            yield event
        if self.references is not None:
            yield ReferencesReady(references=self.references)

    async def forget(self, conversation_id: uuid.UUID) -> None:
        self.forgotten.append(conversation_id)
