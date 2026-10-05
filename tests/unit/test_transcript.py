from rag.domain.models import (
    AnswerVerified,
    ArtifactsReady,
    ReasoningDelta,
    StreamEvent,
    TextDelta,
    ToolCall,
)
from rag.services.conversation_service.transcript import TranscriptBuilder


def _built(*events: StreamEvent) -> list[StreamEvent]:
    builder = TranscriptBuilder()
    for event in events:
        builder.add(event)
    return builder.events


def test_consecutive_deltas_of_a_kind_are_merged() -> None:
    assert _built(
        ReasoningDelta("Weigh"),
        ReasoningDelta("ing"),
        TextDelta("Hel"),
        TextDelta("lo"),
        ArtifactsReady([]),
    ) == [ReasoningDelta("Weighing"), TextDelta("Hello"), ArtifactsReady([])]


def test_text_on_either_side_of_a_search_stays_apart() -> None:
    search = ToolCall(name="search_kb", status="pending", query="pricing")

    assert _built(TextDelta("Let me check."), search, TextDelta("It's 10.")) == [
        TextDelta("Let me check."),
        search,
        TextDelta("It's 10."),
    ]


def test_a_revision_follows_the_rejected_answers_verdict() -> None:
    # The rejected answer never reached the stream, only its verdict did.
    rejected = AnswerVerified(status="done", grounded=False)

    assert _built(
        AnswerVerified(status="pending"),
        rejected,
        TextDelta("revised"),
    ) == [AnswerVerified(status="pending"), rejected, TextDelta("revised")]
