from langchain_core.messages import AIMessageChunk

from rag.domain.models import ReasoningDelta, TextDelta
from rag.services.agent_service.streaming import parse_event


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
