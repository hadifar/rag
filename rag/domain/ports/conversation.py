import uuid
from datetime import datetime
from typing import Protocol

from rag.domain.models import AgentMemory, Conversation, StreamEvent, Turn


class ConversationRepositoryPort(Protocol):
    async def get_or_create_empty(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty (untitled) conversation, created if they have none, and
        bumped to most recently used. A user has at most one.
        """
        ...

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation | None:
        """None if it doesn't exist or is another user's: the same for both, so ids
        can't be probed.
        """
        ...

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        """The unpinned ones, newest first by (updated_at, id); `before` is exclusive
        (keyset pagination).
        """
        ...

    async def list_pinned(self, user_id: uuid.UUID) -> list[Conversation]:
        """The pinned ones, last pinned first."""
        ...

    async def update_owned(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        title: str | None,
        pinned: bool | None,
    ) -> Conversation | None:
        """Sets each field given (None leaves it as is), without bumping it to most
        recently used; pinning a pinned one keeps when it was pinned. None, as
        `get_owned`, if it isn't the user's.
        """
        ...

    async def touch_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation | None:
        """Bumps it to most recently used; None, as `get_owned`, if it isn't the user's."""
        ...

    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None: ...
    async def delete(self, conversation_id: uuid.UUID) -> None:
        """Deletes the conversation and its turns."""
        ...

    # The transcript: what the user saw of the conversation, turn by turn, each turn
    # beside what the chat agent remembers of it (its own messages).
    async def append_turn(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: list[StreamEvent],
        memory: AgentMemory | None = None,
    ) -> None: ...
    async def list_turns(self, conversation_id: uuid.UUID) -> list[Turn]:
        """Oldest first; empty for a conversation without any."""
        ...
