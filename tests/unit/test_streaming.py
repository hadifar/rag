from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.types import Command

from rag.domain.models import (
    ReasoningDelta,
    TextDelta,
    Todo,
    TodosUpdated,
    ToolCall,
)
from rag.services.agent_service.streaming import parse_event, replay


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


def test_replay_shows_saved_messages_as_they_streamed():
    todos = [{"content": "Find the release note", "status": "in_progress"}]
    planning = AIMessage(
        content=[
            {
                "type": "reasoning",
                "summary": [
                    {"index": 0, "type": "summary_text", "text": "First"},
                    {"index": 1, "type": "summary_text", "text": "Second"},
                ],
                "index": 0,
            }
        ],
        response_metadata={"model_provider": "openai"},
        tool_calls=[
            {"name": "write_todos", "args": {"todos": todos}, "id": "c1"},
            {"name": "search_kb", "args": {"query": "release"}, "id": "c2"},
        ],
    )
    messages = [
        planning,
        ToolMessage(content="Updated todo list", name="write_todos", tool_call_id="c1"),
        ToolMessage(content="2 chunks", name="search_kb", tool_call_id="c2"),
        AIMessage(content="It shipped."),
    ]

    assert replay(messages) == [
        ReasoningDelta(text="\n\nFirst"),
        ReasoningDelta(text="\n\nSecond"),
        TodosUpdated(
            todos=[Todo(content="Find the release note", status="in_progress")]
        ),
        ToolCall(name="search_kb", status="pending", query="release"),
        ToolCall(name="search_kb", status="done", output="2 chunks"),
        TextDelta(text="It shipped."),
    ]
