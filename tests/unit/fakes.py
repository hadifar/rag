import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from langchain_core.messages import AIMessage

from rag.domain.events import StreamEvent, TextDelta
from rag.domain.models import Conversation, HistoryMessage


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

    async def create(self, user_id: uuid.UUID, title: str) -> Conversation:
        now = self._now()
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
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


class StubChatEngine:
    """ChatEnginePort that echoes the message, and records threads it was asked
    to delete.
    """

    def __init__(self, extra_events: list[StreamEvent] | None = None):
        self.extra_events = extra_events or []
        self.threads: dict[str, list[HistoryMessage]] = {}
        self.deleted_threads: list[str] = []

    async def stream_chat(
        self, message: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        reply = f"echo: {message}"
        self.threads.setdefault(thread_id, []).extend(
            [
                HistoryMessage(role="user", text=message),
                HistoryMessage(role="assistant", text=reply),
            ]
        )
        yield TextDelta(text=reply)
        for event in self.extra_events:
            yield event

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        return self.threads.get(thread_id, [])

    async def delete_history(self, thread_id: str) -> None:
        self.deleted_threads.append(thread_id)
        self.threads.pop(thread_id, None)


class FakeTitleModel:
    def __init__(self, reply: str = "Generated title", error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.prompts: list[str] = []

    async def ainvoke(self, prompt: str) -> AIMessage:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return AIMessage(content=self.reply)
