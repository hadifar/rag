from dataclasses import dataclass
from typing import Literal


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCall:
    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None


@dataclass
class SourcesReady:
    sources: list[str]


StreamEvent = TextDelta | ToolCall | SourcesReady
