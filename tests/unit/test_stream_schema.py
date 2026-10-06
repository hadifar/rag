"""The API's stream events mirror the domain's: same `type` tags, same fields. They are
joined only by `to_stream_event`'s `model_validate(asdict(event))`, so without these a
domain event the API can't carry would fail mid-stream, not in CI.
"""

from dataclasses import asdict
from typing import get_args

import pytest

from rag.api.schema.chat import StreamEventResponse, to_stream_event
from rag.domain.models import (
    AnswerVerified,
    ArtifactsReady,
    ReasoningDelta,
    SourceArtifact,
    StreamEvent,
    TextDelta,
    Todo,
    TodosUpdated,
    ToolCall,
    TurnFailed,
)

# One of each domain event, every optional field set, so a renamed field shows up.
_SAMPLES: list[StreamEvent] = [
    TextDelta(text="Hi"),
    ReasoningDelta(text="Thinking"),
    ToolCall(name="search_kb", status="done", query="pricing", output="Plans…"),
    TodosUpdated(todos=[Todo(content="Find pricing", status="in_progress")]),
    AnswerVerified(status="done", grounded=False),
    ArtifactsReady(artifacts=[SourceArtifact(id="pricing.md")]),
    TurnFailed(message="Something went wrong"),
]


def _api_tags() -> set[str]:
    # Pydantic keeps the discriminator apart, so the annotation is the bare union.
    union = StreamEventResponse.model_fields["root"].annotation
    return {model.model_fields["type"].default for model in get_args(union)}


def test_every_domain_event_has_a_sample() -> None:
    assert {type(event) for event in _SAMPLES} == set(get_args(StreamEvent))


def test_the_api_has_exactly_the_domain_event_types() -> None:
    # The samples cover every domain event (see the test above).
    assert _api_tags() == {event.type for event in _SAMPLES}


@pytest.mark.parametrize("event", _SAMPLES, ids=lambda event: type(event).__name__)
def test_a_domain_event_reaches_the_api_unchanged(event: StreamEvent) -> None:
    assert to_stream_event(event).model_dump() == asdict(event)
