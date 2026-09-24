"""The vocabulary of things that can happen during a chat turn.

Produced by the generation service as it translates LangGraph's raw event
stream, and consumed by the API layer to serialize them as SSE.
"""

from dataclasses import dataclass


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallStart:
    name: str
    args: dict


@dataclass
class ToolCallResult:
    name: str
    output: str


StreamEvent = TextDelta | ToolCallStart | ToolCallResult
