import hashlib
import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from rag.domain.errors import ConversationNotFoundError, IngestionInProgressError
from rag.domain.models import (
    AgentMemory,
    Artifact,
    ArtifactsReady,
    Attachment,
    AttachmentFile,
    Conversation,
    ConversationUpdate,
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    RunContext,
    Share,
    Skill,
    SkillContent,
    StreamEvent,
    TextDelta,
    Turn,
    User,
)


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


class FakeCache[T]:
    """In-memory CachePort that never expires; records its puts. With `failing`, every
    call raises, as a cache whose database is down.
    """

    def __init__(self, *, failing: bool = False):
        self.values: dict[str, T] = {}
        self.puts: list[str] = []
        self.failing = failing

    async def get(self, key: str) -> T | None:
        if self.failing:
            raise RuntimeError("cache down")
        return self.values.get(key)

    async def put(self, key: str, value: T) -> None:
        if self.failing:
            raise RuntimeError("cache down")
        self.puts.append(key)
        self.values[key] = value


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
        self.turns: dict[uuid.UUID, list[Turn]] = {}
        # The conversations' attachments, which FakeAttachmentRepository writes.
        self.attachments: dict[uuid.UUID, AttachmentFile] = {}
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
            return await self.touch_owned(user_id, empty.id)
        now = self._now()
        conversation = Conversation(
            id=uuid.uuid4(), user_id=user_id, title=None, created_at=now, updated_at=now
        )
        self.rows[conversation.id] = conversation
        return conversation

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = self.rows.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        mine = sorted(
            (
                c
                for c in self.rows.values()
                if c.user_id == user_id and c.pinned_at is None
            ),
            key=lambda c: (c.updated_at, c.id),
            reverse=True,
        )
        if before is not None:
            mine = [c for c in mine if (c.updated_at, c.id) < before]
        return mine[:limit]

    async def list_pinned(self, user_id: uuid.UUID) -> list[Conversation]:
        pinned = [
            c
            for c in self.rows.values()
            if c.user_id == user_id and c.pinned_at is not None
        ]
        return sorted(pinned, key=lambda c: (c.pinned_at, c.id), reverse=True)

    async def update_owned(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        change: ConversationUpdate,
    ) -> Conversation:
        conversation = await self.get_owned(user_id, conversation_id)
        fields = {
            k: v for k, v in asdict(change).items() if v is not None and k != "pinned"
        }
        conversation = replace(conversation, **fields)
        if change.pinned is not None:
            pinned_at = (
                (conversation.pinned_at or self._now()) if change.pinned else None
            )
            conversation = replace(conversation, pinned_at=pinned_at)
        self.rows[conversation_id] = conversation
        return conversation

    async def touch_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        await self.get_owned(user_id, conversation_id)
        self.rows[conversation_id] = replace(
            self.rows[conversation_id], updated_at=self._now()
        )
        return self.rows[conversation_id]

    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None:
        self.rows[conversation_id] = replace(self.rows[conversation_id], title=title)

    async def delete(self, conversation_id: uuid.UUID) -> None:
        self.rows.pop(conversation_id, None)
        self.turns.pop(conversation_id, None)
        for attachment_id, file in list(self.attachments.items()):
            if file.attachment.conversation_id == conversation_id:
                del self.attachments[attachment_id]

    async def append_turn(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: list[StreamEvent],
        memory: AgentMemory | None = None,
        attachment_ids: Sequence[uuid.UUID] = (),
    ) -> None:
        attachments = [
            self.attachments[i].attachment
            for i in attachment_ids
            if i in self.attachments
            and self.attachments[i].attachment.conversation_id == conversation_id
        ]
        turn = Turn(question, list(answer), memory, attachments)
        self.turns.setdefault(conversation_id, []).append(turn)

    async def list_turns(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[Turn]:
        return list(self.turns.get(conversation_id, []))[:limit]


class FakeAttachmentRepository:
    """In-memory AttachmentRepositoryPort, keeping its files on `conversations`, whose
    turns tell which were sent.
    """

    def __init__(self, conversations: FakeConversationRepository):
        self.conversations = conversations
        self._clock = datetime(2026, 3, 1, tzinfo=UTC)

    async def create(
        self, conversation_id: uuid.UUID, name: str, media_type: str, data: bytes
    ) -> Attachment:
        self._clock += timedelta(seconds=1)
        attachment = Attachment(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            name=name,
            media_type=media_type,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            created_at=self._clock,
        )
        self.conversations.attachments[attachment.id] = AttachmentFile(attachment, data)
        return attachment

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> AttachmentFile | None:
        try:
            await self.conversations.get_owned(user_id, conversation_id)
        except ConversationNotFoundError:
            return None
        files = await self.list_in(conversation_id, [attachment_id])
        return files[0] if files else None

    async def list_in(
        self, conversation_id: uuid.UUID, attachment_ids: Sequence[uuid.UUID]
    ) -> list[AttachmentFile]:
        files = self.conversations.attachments
        return [
            files[i]
            for i in attachment_ids
            if i in files and files[i].attachment.conversation_id == conversation_id
        ]

    async def list_sent(self, conversation_id: uuid.UUID) -> list[AttachmentFile]:
        sent = self._sent()
        return [
            f
            for f in self.conversations.attachments.values()
            if f.attachment.conversation_id == conversation_id
            and f.attachment.id in sent
        ]

    async def delete_unsent(
        self, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> bool:
        if not await self.list_in(conversation_id, [attachment_id]):
            return False
        if attachment_id in self._sent():
            return False
        del self.conversations.attachments[attachment_id]
        return True

    async def delete_unsent_before(self, cutoff: datetime) -> int:
        sent = self._sent()
        stale = [
            i
            for i, f in self.conversations.attachments.items()
            if f.attachment.created_at < cutoff and i not in sent
        ]
        for attachment_id in stale:
            del self.conversations.attachments[attachment_id]
        return len(stale)

    def _sent(self) -> set[uuid.UUID]:
        return {
            a.id
            for turns in self.conversations.turns.values()
            for turn in turns
            for a in turn.attachments
        }


class FakeSkillRepository:
    """In-memory SkillRepositoryPort."""

    def __init__(self):
        # By owner and name: the skill, its instructions and its files by path.
        self.rows: dict[tuple[uuid.UUID, str], tuple[Skill, str, dict[str, str]]] = {}
        self._clock = datetime(2026, 3, 1, tzinfo=UTC)

    async def save(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str,
        instructions: str,
        files: Mapping[str, str],
    ) -> Skill:
        self._clock += timedelta(seconds=1)
        existing = self.rows.get((user_id, name))
        skill = Skill(
            id=existing[0].id if existing else uuid.uuid4(),
            name=name,
            description=description,
            file_count=len(files),
            created_at=existing[0].created_at if existing else self._clock,
            updated_at=self._clock,
        )
        self.rows[user_id, name] = (skill, instructions, dict(files))
        return skill

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]:
        return sorted(
            (
                skill
                for (owner, _), (skill, *_) in self.rows.items()
                if owner == user_id
            ),
            key=lambda s: s.name,
        )

    async def content(self, user_id: uuid.UUID, name: str) -> SkillContent | None:
        row = self.rows.get((user_id, name))
        return SkillContent(row[1], tuple(sorted(row[2]))) if row else None

    async def file(self, user_id: uuid.UUID, name: str, path: str) -> str | None:
        row = self.rows.get((user_id, name))
        return row[2].get(path) if row else None

    async def delete_owned(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        key = next(
            (
                k
                for k, (skill, *_) in self.rows.items()
                if k[0] == user_id and skill.id == skill_id
            ),
            None,
        )
        if key is None:
            return False
        del self.rows[key]
        return True


class FakeShareRepository:
    """In-memory ShareRepositoryPort, reading turn counts from `conversations`."""

    def __init__(self, conversations: FakeConversationRepository):
        self.conversations = conversations
        self.rows: dict[uuid.UUID, Share] = {}  # by conversation id
        self._clock = datetime(2026, 2, 1, tzinfo=UTC)

    async def save(self, conversation_id: uuid.UUID, title: str) -> Share | None:
        turn_count = len(self.conversations.turns.get(conversation_id, []))
        if turn_count == 0:
            return None
        self._clock += timedelta(seconds=1)
        current = self.rows.get(conversation_id)
        self.rows[conversation_id] = Share(
            id=current.id if current else uuid.uuid4(),
            conversation_id=conversation_id,
            title=title,
            turn_count=turn_count,
            shared_at=self._clock,
        )
        return self.rows[conversation_id]

    async def get_for_conversation(self, conversation_id: uuid.UUID) -> Share | None:
        return self.rows.get(conversation_id)

    async def get(self, share_id: uuid.UUID) -> Share | None:
        # Deleting a conversation takes its link down, as the foreign key does.
        return next(
            (
                s
                for s in self.rows.values()
                if s.id == share_id and s.conversation_id in self.conversations.rows
            ),
            None,
        )

    async def delete_for_conversation(self, conversation_id: uuid.UUID) -> None:
        self.rows.pop(conversation_id, None)


class StubGeneration:
    """LLMPort without a model: answers every prompt with `reply`, or raises
    `error`, and records the prompts.
    """

    def __init__(self, reply: str = "Generated title", error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.prompts: list[str] = []

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attachments: Sequence[AttachmentFile] = (),
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        # The reply, as the one field of the structured answer.
        return schema.model_validate({"title": self.reply})


class StubTurn:
    """ChatTurnPort for a scripted turn: streams `events`, then remembers `memory`."""

    def __init__(self, events: list[StreamEvent], memory: AgentMemory):
        self._events = events
        self._memory = memory
        self.memory: AgentMemory | None = None

    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        for event in self._events:
            yield event
        self.memory = self._memory


class StubAgent:
    """AgentPort without a model: echoes the message, then `extra_events`, then
    `artifacts` if given, and remembers the turn as `[{"said": message}]`; records the
    history, the context and the attachments each turn was given.
    """

    def __init__(
        self,
        extra_events: list[StreamEvent] | None = None,
        artifacts: list[Artifact] | None = None,
    ):
        self.extra_events = extra_events or []
        self.artifacts = artifacts
        self.histories: list[list[AgentMemory]] = []
        self.contexts: list[RunContext] = []
        self.attachments: list[list[AttachmentFile]] = []
        self.earlier_attachments: list[list[AttachmentFile]] = []

    def stream(
        self,
        message: str,
        history: Sequence[AgentMemory],
        ctx: RunContext,
        *,
        attachments: Sequence[AttachmentFile] = (),
        earlier_attachments: Sequence[AttachmentFile] = (),
    ) -> StubTurn:
        self.histories.append(list(history))
        self.contexts.append(ctx)
        self.attachments.append(list(attachments))
        self.earlier_attachments.append(list(earlier_attachments))
        events: list[StreamEvent] = [
            TextDelta(text=f"echo: {message}"),
            *self.extra_events,
        ]
        if self.artifacts is not None:
            events.append(ArtifactsReady(artifacts=self.artifacts))
        return StubTurn(events, [{"said": message}])
