from dataclasses import dataclass
from typing import Literal


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCall:
    """A knowledge-base search: `pending` with its query, then `done` with its output."""

    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None


@dataclass
class SourcesReady:
    sources: list[str]


StreamEvent = TextDelta | ToolCall | SourcesReady
