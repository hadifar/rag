from dataclasses import asdict
from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

from rag.domain.models import StreamEvent

# The message stream's events: each is one SSE `data:` line of JSON, told apart by `type`.


class TextEvent(BaseModel):
    """A piece of the answer, in order."""

    type: Literal["text"] = "text"
    text: str


class ReasoningEvent(BaseModel):
    """A piece of the model's reasoning summary, in order."""

    type: Literal["reasoning"] = "reasoning"
    text: str


class ToolEvent(BaseModel):
    """A tool call: `pending`, then `done` with its output. `label` is what the chat
    shows (None in transcripts stored before it); `output` is None for a skill tool,
    whose result is only for the model.
    """

    type: Literal["tool"] = "tool"
    name: str
    status: Literal["pending", "done"]
    label: str | None = None
    query: str | None = None
    output: str | None = None


class TodoItem(BaseModel):
    content: str
    status: Literal["pending", "in_progress", "completed"]


class TodosEvent(BaseModel):
    """The agent's whole plan, each time it rewrites it."""

    type: Literal["todos"] = "todos"
    todos: list[TodoItem]


class AnswerCheckEvent(BaseModel):
    """The answer checked against what the turn's searches found: `pending` while the
    check runs, then `done` with whether the answer is supported by them.
    """

    type: Literal["answer_check"] = "answer_check"
    status: Literal["pending", "done"]
    grounded: bool | None = None


class SourceArtifactItem(BaseModel):
    """A knowledge-base source the answer drew on."""

    kind: Literal["source"] = "source"
    id: str


# A new artifact kind joins the union here.
ArtifactItem = Annotated[SourceArtifactItem, Field(discriminator="kind")]


class ArtifactsEvent(BaseModel):
    """What the turn's tools handed the user, deduplicated, once it's done. Only sent
    if a tool that hands anything over ran.
    """

    type: Literal["artifacts"] = "artifacts"
    artifacts: list[ArtifactItem]


class ErrorEvent(BaseModel):
    """The turn couldn't finish; the last event of its stream. `message` is for the user."""

    type: Literal["error"] = "error"
    message: str


class StreamEventResponse(
    RootModel[
        Annotated[
            TextEvent
            | ReasoningEvent
            | ToolEvent
            | TodosEvent
            | AnswerCheckEvent
            | ArtifactsEvent
            | ErrorEvent,
            Field(discriminator="type"),
        ]
    ]
):
    """One event of the message stream. A named model rather than a bare union, so it's
    in the OpenAPI schema and the frontend's generated types by this name.
    """


def to_stream_event(event: StreamEvent) -> StreamEventResponse:
    """The API model for a domain event: both carry the same fields and `type` tag."""
    return StreamEventResponse.model_validate(asdict(event))
