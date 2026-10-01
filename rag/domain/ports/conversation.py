import uuid
from datetime import datetime
from typing import Protocol

from rag.domain.models import Conversation, HistoryMessage


class ConversationRepositoryPort(Protocol):
    async def get_or_create_empty(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty (untitled) conversation, created if they have none, and
        bumped to most recently used. A user has at most one.
        """
        ...

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        """Newest first by (updated_at, id); `before` is exclusive (keyset pagination)."""
        ...

    async def touch(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None: ...
    async def delete(self, conversation_id: uuid.UUID) -> None: ...
    async def all_ids(self) -> set[uuid.UUID]:
        """Every conversation's id, whoever owns it."""
        ...

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        """The thread's messages as the user saw them; empty for an unknown thread."""
        ...

    async def delete_history(self, thread_id: str) -> None: ...
    async def list_thread_ids(self) -> set[str]:
        """Every thread that has stored messages."""
        ...


class HistoryStorePort(Protocol):
    """The chat messages stored per thread, which the chat agent writes as it answers."""

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        """The thread's messages as the user saw them; empty for an unknown thread."""
        ...

    async def delete_history(self, thread_id: str) -> None: ...
    async def list_thread_ids(self) -> set[str]:
        """Every thread that has stored messages."""
        ...
