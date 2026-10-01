from typing import Literal

from pydantic.dataclasses import dataclass


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
class ReferencesReady:
    """What the turn's tools cited (e.g. knowledge-base source ids), deduplicated; sent
    once the turn is done, and only if a tool that cites anything ran.
    """

    references: list[str]


StreamEvent = TextDelta | ToolCall | ReferencesReady
