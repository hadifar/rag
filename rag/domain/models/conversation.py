import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from rag.domain.models.agent.stream import StreamEvent


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    user_id: uuid.UUID
    # None only while the conversation is empty: its first message names it.
    title: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConversationPage:
    items: list[Conversation]
    # Opaque; pass back to fetch the next (older) page. None on the last page.
    next_cursor: str | None


@dataclass(frozen=True)
class Turn:
    """One exchange of a conversation as the user saw it: their question, and the
    events its answer streamed.
    """

    question: str
    answer: list[StreamEvent]


@dataclass(frozen=True)
class UserMessage:
    text: str
    role: Literal["user"] = "user"


@dataclass(frozen=True)
class AssistantMessage:
    """A turn's answer as the events its stream sent, in order: reasoning, searches,
    the plan, the answer's text, and its artifacts; replayed, it shows as it did live.
    """

    events: list[StreamEvent]
    role: Literal["assistant"] = "assistant"


HistoryMessage = UserMessage | AssistantMessage
