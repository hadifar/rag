from langchain_core.messages import AIMessageChunk
from langgraph.types import Command

from rag.domain.models import (
    AnswerVerified,
    ReasoningDelta,
    StreamEvent,
    TextDelta,
    Todo,
    TodosUpdated,
    ToolCall,
)
from rag.services.agent_service.streaming import AnswerGate, parse_event


def _model_stream(chunk: AIMessageChunk, node: str = "model") -> dict:
    return {
        "event": "on_chat_model_stream",
        "metadata": {"langgraph_node": node},
        "data": {"chunk": chunk},
    }


def _responses_chunk(*content: dict) -> AIMessageChunk:
    return AIMessageChunk(
        content=list(content), response_metadata={"model_provider": "openai"}
    )


def _summary(text: str, index: int = 0) -> dict:
    return {
        "type": "reasoning",
        "summary": [{"index": index, "type": "summary_text", "text": text}],
        "index": 0,
    }


def test_chat_completions_text_is_a_text_delta():
    assert parse_event(_model_stream(AIMessageChunk(content="Hi"))) == [
        TextDelta(text="Hi")
    ]


def test_responses_api_reasoning_and_text_are_told_apart():
    chunk = _responses_chunk(
        _summary("Thinking"), {"type": "text", "text": "Answer", "index": 1}
    )
    assert parse_event(_model_stream(chunk)) == [
        ReasoningDelta(text="Thinking"),
        TextDelta(text="Answer"),
    ]


def test_a_new_summary_part_starts_a_new_paragraph():
    assert parse_event(_model_stream(_responses_chunk(_summary("", index=1)))) == [
        ReasoningDelta(text="\n\n")
    ]


def test_reasoning_item_start_without_summary_is_skipped():
    chunk = _responses_chunk(
        {"type": "reasoning", "id": "rs_1", "summary": [], "index": 0}
    )
    assert parse_event(_model_stream(chunk)) == []


def test_guard_model_calls_are_not_streamed():
    chunk = _responses_chunk(_summary("Thinking"))
    assert parse_event(_model_stream(chunk, node="OffTopic.before_model")) == []


def test_planning_tool_output_is_the_plan():
    todos = [{"content": "Find the release note", "status": "in_progress"}]
    event = {
        "event": "on_tool_end",
        "name": "write_todos",
        "data": {"output": Command(update={"todos": todos, "messages": []})},
    }
    assert parse_event(event) == [
        TodosUpdated(
            todos=[Todo(content="Find the release note", status="in_progress")]
        )
    ]


def test_planning_tool_start_is_not_a_tool_call():
    event = {"event": "on_tool_start", "name": "write_todos", "data": {"input": {}}}
    assert parse_event(event) == []


def test_the_answers_check_is_sent_as_it_starts_and_with_its_verdict():
    def check(data: dict) -> dict:
        return {"event": "on_custom_event", "name": "answer_verification", "data": data}

    assert parse_event(check({"status": "pending"})) == [
        AnswerVerified(status="pending")
    ]
    assert parse_event(check({"status": "done", "grounded": False})) == [
        AnswerVerified(status="done", grounded=False)
    ]


def test_other_custom_events_are_not_streamed():
    event = {"event": "on_custom_event", "name": "something_else", "data": {}}
    assert parse_event(event) == []


_SEARCH = ToolCall(name="search_kb", status="pending", query="pricing")
_CHECKING = AnswerVerified(status="pending")
_PASSED = AnswerVerified(status="done", grounded=True)
_FAILED = AnswerVerified(status="done", grounded=False)


def _gated(*events: StreamEvent) -> list[StreamEvent]:
    gate = AnswerGate()
    sent = [released for event in events for released in gate.feed(event)]
    return sent + gate.flush()


def test_text_streams_live_until_a_tool_runs():
    gate = AnswerGate()
    assert gate.feed(TextDelta("hi")) == [TextDelta("hi")]


def test_an_answer_after_a_search_is_held_until_it_passes_its_check():
    gate = AnswerGate()
    gate.feed(_SEARCH)

    assert gate.feed(TextDelta("It's 10.")) == []
    assert gate.feed(_CHECKING) == [_CHECKING]
    assert gate.feed(_PASSED) == [_PASSED, TextDelta("It's 10.")]


def test_a_rejected_answer_is_never_sent_and_its_revision_is():
    assert _gated(
        _SEARCH, TextDelta("wrong"), _CHECKING, _FAILED, TextDelta("revised")
    ) == [_SEARCH, _CHECKING, _FAILED, TextDelta("revised")]


def test_held_text_is_sent_before_the_next_tool_call():
    plan = TodosUpdated(todos=[Todo(content="Find it", status="pending")])

    assert _gated(_SEARCH, TextDelta("Let me plan."), plan) == [
        _SEARCH,
        TextDelta("Let me plan."),
        plan,
    ]


def test_reasoning_is_never_held():
    gate = AnswerGate()
    gate.feed(_SEARCH)
    assert gate.feed(ReasoningDelta("So")) == [ReasoningDelta("So")]
