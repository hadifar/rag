from rag.domain.models import (
    AnswerRetracted,
    ReasoningDelta,
    ReferencesReady,
    StreamEvent,
    TextDelta,
    Todo,
    TodosUpdated,
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
        ReferencesReady([]),
    ) == [ReasoningDelta("Weighing"), TextDelta("Hello"), ReferencesReady([])]


def test_text_on_either_side_of_a_search_stays_apart() -> None:
    search = ToolCall(name="search_kb", status="pending", query="pricing")

    assert _built(TextDelta("Let me check."), search, TextDelta("It's 10.")) == [
        TextDelta("Let me check."),
        search,
        TextDelta("It's 10."),
    ]


def test_a_retraction_drops_the_answer_since_the_last_tool_call() -> None:
    done = ToolCall(name="search_kb", status="done", output="facts")

    assert _built(
        TextDelta("Searching."),
        done,
        ReasoningDelta("So"),
        TextDelta("wro"),
        TextDelta("ng"),
        AnswerRetracted(),
        TextDelta("revised"),
    ) == [TextDelta("Searching."), done, ReasoningDelta("So"), TextDelta("revised")]


def test_a_retraction_stops_at_the_plan_too() -> None:
    plan = TodosUpdated(todos=[Todo(content="Find it", status="completed")])

    assert _built(TextDelta("Kept"), plan, TextDelta("wrong"), AnswerRetracted()) == [
        TextDelta("Kept"),
        plan,
    ]


def test_a_retracted_first_answer_leaves_nothing_of_it() -> None:
    assert _built(TextDelta("wrong"), AnswerRetracted(), TextDelta("right")) == [
        TextDelta("right")
    ]


def test_what_follows_a_retraction_is_not_merged_into_what_came_before() -> None:
    # Live, the revision's reasoning is a new bubble after the dropped text.
    assert _built(
        ReasoningDelta("first"),
        TextDelta("wrong"),
        AnswerRetracted(),
        ReasoningDelta("second"),
        ReasoningDelta(" thought"),
    ) == [ReasoningDelta("first"), ReasoningDelta("second thought")]
