import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from rag.domain.models.agent.agent import AgentMemory
from rag.domain.models.agent.stream import StreamEvent
from rag.domain.models.attachment import Attachment


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    user_id: uuid.UUID
    # None only while the conversation is empty: its first message names it.
    title: str | None
    created_at: datetime
    updated_at: datetime
    # When the user pinned it; None while it isn't pinned.
    pinned_at: datetime | None = None


@dataclass(frozen=True)
class ConversationUpdate:
    """What to change about a conversation; a field left None stays as is."""

    title: str | None = None
    pinned: bool | None = None


@dataclass(frozen=True)
class Share:
    """A read-only public link to a conversation as it was when shared: its title then,
    and its first `turn_count` turns.
    """

    id: uuid.UUID  # the link's token
    conversation_id: uuid.UUID
    title: str
    turn_count: int
    shared_at: datetime


@dataclass(frozen=True)
class ConversationPage:
    items: list[Conversation]
    # Opaque; pass back to fetch the next (older) page. None on the last page.
    next_cursor: str | None


@dataclass(frozen=True)
class Turn:
    """One exchange of a conversation as the user saw it: their question, and the
    events its answer streamed; and what the agent remembers of it.
    """

    question: str  # empty if the user sent only attachments
    answer: list[StreamEvent]
    # None for a turn the agent forgot: blocked, failed or cut short.
    memory: AgentMemory | None = None
    # Sent with the question, in the order the user attached them.
    attachments: list[Attachment] = field(default_factory=list[Attachment])


@dataclass(frozen=True)
class UserMessage:
    text: str
    attachments: list[Attachment] = field(default_factory=list[Attachment])
    role: Literal["user"] = "user"


@dataclass(frozen=True)
class AssistantMessage:
    """A turn's answer as the events its stream sent, in order: reasoning, searches,
    the plan, the answer's text, and its artifacts; replayed, it shows as it did live.
    """

    events: list[StreamEvent]
    role: Literal["assistant"] = "assistant"


HistoryMessage = UserMessage | AssistantMessage


def history_of(turns: list[Turn]) -> list[HistoryMessage]:
    """The turns as the user saw them: each question, then its answer's events, if it
    sent any. Never the agent's memory of them.
    """
    history: list[HistoryMessage] = []
    for turn in turns:
        history.append(UserMessage(text=turn.question, attachments=turn.attachments))
        if turn.answer:
            history.append(AssistantMessage(events=turn.answer))
    return history


@dataclass(frozen=True)
class SharedConversation:
    """What a share link shows: the snapshot's title and date, and its history."""

    share: Share
    history: list[HistoryMessage]
