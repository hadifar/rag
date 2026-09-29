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


StreamEvent = TextDelta | ToolCallStart | ToolCallResult | SourcesReady
