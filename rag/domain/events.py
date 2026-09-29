from dataclasses import dataclass


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
    """The deduplicated sources used across the whole turn, once the graph run finishes.
    Only sent if the turn searched; empty means the search found nothing.
    """

    sources: list[str]


@dataclass
class ConversationTitled:
    """A conversation's first message names it: first event of its first turn, from the
    message, and last event too if an LLM-written title replaces it.
    """

    conversation_id: str
    title: str


StreamEvent = (
    TextDelta | ToolCallStart | ToolCallResult | SourcesReady | ConversationTitled
)
