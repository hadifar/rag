import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from rag.domain.models import (
    AgentMemory,
    Conversation,
    ConversationUpdate,
    Share,
    StreamEvent,
    Turn,
)


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
        change: ConversationUpdate,
    ) -> Conversation | None:
        """Sets each field `change` gives (None leaves it as is), without bumping it to most
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
        attachment_ids: Sequence[uuid.UUID] = (),
    ) -> None:
        """`attachment_ids`, the conversation's attachments sent with `question`, in
        the order the user attached them.
        """
        ...

    async def list_turns(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[Turn]:
        """Oldest first, the first `limit` of them if given; empty for a conversation
        without any.
        """
        ...


class ShareRepositoryPort(Protocol):
    """Each conversation's public read-only link, if it has one."""

    async def save(self, conversation_id: uuid.UUID, title: str) -> Share | None:
        """Shares the conversation as it is now: `title`, and the turns it has. Sharing
        it again takes a new snapshot behind the same link. None if it has no turns.
        """
        ...

    async def get_for_conversation(
        self, conversation_id: uuid.UUID
    ) -> Share | None: ...
    async def get(self, share_id: uuid.UUID) -> Share | None: ...
    async def delete_for_conversation(self, conversation_id: uuid.UUID) -> None:
        """Takes its link down; sharing it again makes a new one."""
        ...
