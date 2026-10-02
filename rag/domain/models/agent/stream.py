from typing import Annotated, Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

# Each event carries its `type`, so a list of them can be stored and read back as it was
# (the conversation transcript) without a mapping of its own.


@dataclass
class TextDelta:
    text: str
    type: Literal["text"] = "text"


@dataclass
class ReasoningDelta:
    """A piece of the model's reasoning summary."""

    text: str
    type: Literal["reasoning"] = "reasoning"


@dataclass
class ToolCall:
    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None
    type: Literal["tool"] = "tool"


@dataclass
class Todo:
    content: str
    status: Literal["pending", "in_progress", "completed"]


@dataclass
class TodosUpdated:
    """The agent's whole plan, sent each time it rewrites it."""

    todos: list[Todo]
    type: Literal["todos"] = "todos"


@dataclass
class AnswerRetracted:
    """The answer text sent since the last tool call or plan was rejected (e.g. as
    unsupported by what the turn's searches found) and is being rewritten: drop it.
    """

    type: Literal["retracted"] = "retracted"


@dataclass
class ReferencesReady:
    """What the turn's tools cited (e.g. knowledge-base source ids), deduplicated; sent
    once the turn is done, and only if a tool that cites anything ran.
    """

    references: list[str]
    type: Literal["references"] = "references"


StreamEvent = (
    TextDelta
    | ReasoningDelta
    | ToolCall
    | TodosUpdated
    | AnswerRetracted
    | ReferencesReady
)

# For reading a stored event back: its `type` says which one it is.
TaggedStreamEvent = Annotated[StreamEvent, Field(discriminator="type")]
