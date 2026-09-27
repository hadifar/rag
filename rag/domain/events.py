from dataclasses import dataclass

from rag.domain.models import Conversation


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallStart:
    name: str
    query: str


@dataclass
class ToolCallResult:
    name: str
    output: str


@dataclass
class SourcesReady:
    """The deduplicated sources used across the whole turn, once the graph run finishes"""

    sources: list[str]


@dataclass
class ConversationReady:
    """First event of every turn: the conversation the turn belongs to (newly created
    or existing), so the client learns a new conversation's server-assigned id.
    """

    conversation: Conversation


@dataclass
class ConversationTitled:
    """Last event of a new conversation's first turn: its generated title."""

    conversation_id: str
    title: str


StreamEvent = (
    ConversationReady
    | TextDelta
    | ToolCallStart
    | ToolCallResult
    | SourcesReady
    | ConversationTitled
)
