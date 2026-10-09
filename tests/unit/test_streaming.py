from langchain_core.messages import AIMessageChunk, ToolMessage
from langgraph.types import Command

from rag.domain.models import (
    ReasoningDelta,
    TextDelta,
    Todo,
    TodosUpdated,
    ToolCall,
)
from rag.services.agent_service.streaming import parse_event


def _model_stream(chunk: AIMessageChunk, node: str = "answer") -> dict:
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
    assert parse_event(_model_stream(chunk, node="check_input")) == []


def test_research_streams_its_reasoning_but_not_its_text():
    chunk = _responses_chunk(
        _summary("Searching"), {"type": "text", "text": "Done.", "index": 1}
    )
    assert parse_event(_model_stream(chunk, node="research")) == [
        ReasoningDelta(text="Searching")
    ]


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


def _tool(event: str, name: str, args: dict, output: str = "") -> dict:
    return {
        "event": event,
        "name": name,
        "data": {"input": args, "output": ToolMessage(output, tool_call_id="call-1")},
    }


def test_a_search_is_labelled_with_its_query_and_keeps_its_output():
    args = {"query": "pricing"}
    assert parse_event(_tool("on_tool_start", "search_kb", args)) == [
        ToolCall(
            name="search_kb",
            status="pending",
            label="Searching: pricing",
            query="pricing",
        )
    ]
    assert parse_event(_tool("on_tool_end", "search_kb", args, "Plans…")) == [
        ToolCall(
            name="search_kb", status="done", label="Searched: pricing", output="Plans…"
        )
    ]


def test_a_skill_load_is_labelled_with_its_name_and_hides_its_instructions():
    args = {"name": "release-notes"}
    assert parse_event(_tool("on_tool_start", "load_skill", args)) == [
        ToolCall(
            name="load_skill",
            status="pending",
            label="Loading skill: release-notes",
            query="",
        )
    ]
    assert parse_event(_tool("on_tool_end", "load_skill", args, "Do X.")) == [
        ToolCall(name="load_skill", status="done", label="Loaded skill: release-notes")
    ]


def test_a_skill_file_read_is_labelled_with_its_path_and_hides_the_file():
    args = {"skill": "release-notes", "path": "template.md"}
    assert parse_event(_tool("on_tool_end", "read_skill_file", args, "# T")) == [
        ToolCall(
            name="read_skill_file",
            status="done",
            label="Read template.md from release-notes",
        )
    ]


def test_an_unknown_tool_is_labelled_with_its_name():
    [event] = parse_event(_tool("on_tool_end", "other_tool", {}, "out"))
    assert event == ToolCall(
        name="other_tool", status="done", label="other_tool", output="out"
    )


def test_a_blocked_messages_refusal_is_sent_as_the_answers_text():
    event = {
        "event": "on_custom_event",
        "name": "input_blocked",
        "data": {"message": "I can't help with that."},
    }
    assert parse_event(event) == [TextDelta(text="I can't help with that.")]


def test_other_custom_events_are_not_streamed():
    event = {"event": "on_custom_event", "name": "something_else", "data": {}}
    assert parse_event(event) == []
