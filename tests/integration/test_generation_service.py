import uuid

from rag.container import build_container
from rag.services.generation_service.streaming import TextDelta, ToolCallStart


async def _ask(integration_settings, message: str) -> tuple[str, list[str]]:
    async with build_container(integration_settings) as container:
        answer = ""
        tool_calls = []

        async for event in container.generation_service.stream_chat(
            message, thread_id=str(uuid.uuid4())
        ):
            if isinstance(event, TextDelta):
                answer += event.text
            elif isinstance(event, ToolCallStart):
                tool_calls.append(event.name)

        return answer, tool_calls


async def test_answers_starter_rate_limit_with_the_correct_number(integration_settings):
    answer, tool_calls = await _ask(
        integration_settings,
        "The per-minute rate limit for the Starter plan. Output format: Just the integer/decimal number, no markdown, no text.",
    )
    assert "search_kb" in tool_calls
    assert "60" in answer.strip()
