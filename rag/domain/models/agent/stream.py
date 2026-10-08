from typing import Annotated, Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from rag.domain.models.agent.artifact import Artifact

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
class AnswerChecked:
    """The answer checked against what the turn's searches found: `pending` while the
    check runs, then `done` with whether the answer is supported by them. No longer
    sent (the agent has no answer check); kept so stored transcripts still read.
    """

    status: Literal["pending", "done"]
    grounded: bool | None = None
    type: Literal["answer_check"] = "answer_check"


@dataclass
class ArtifactsReady:
    """What the turn's tools handed the user (e.g. knowledge-base sources), deduplicated;
    sent once the turn is done, and only if a tool that hands anything over ran.
    """

    artifacts: list[Artifact]
    type: Literal["artifacts"] = "artifacts"


@dataclass
class TurnFailed:
    """The turn couldn't finish (a tool or the model failed); the last event it sends.
    `message` is for the user, never the exception itself.
    """

    message: str
    type: Literal["error"] = "error"


StreamEvent = (
    TextDelta
    | ReasoningDelta
    | ToolCall
    | TodosUpdated
    | AnswerChecked
    | ArtifactsReady
    | TurnFailed
)

# For reading a stored event back: its `type` says which one it is.
TaggedStreamEvent = Annotated[StreamEvent, Field(discriminator="type")]
