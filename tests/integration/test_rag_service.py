import uuid

from rag.container import build_container
from rag.domain.models import TextDelta, ToolCall


async def _ask(integration_settings, message: str) -> tuple[str, list[str]]:
    async with build_container(integration_settings) as container:
        answer = ""
        tool_calls = []

        async for event in container.rag_service.stream_chat(
            message, conversation_id=uuid.uuid4(), user_id=uuid.uuid4()
        ):
            if isinstance(event, TextDelta):
                answer += event.text
            elif isinstance(event, ToolCall) and event.status == "pending":
                tool_calls.append(event.name)

        return answer, tool_calls


async def test_answers_from_the_knowledge_base_with_the_correct_number(
    integration_settings, seeded_kb
):
    # The fact exists only in the fixture knowledge base `seeded_kb` ingests, so a
    # correct answer means the agent actually searched and used what it found.
    answer, tool_calls = await _ask(
        integration_settings,
        "How much does the Zephyr analytics add-on cost per seat per month? "
        "Output format: Just the integer/decimal number, no markdown, no text.",
    )
    assert "search_kb" in tool_calls
    assert "14" in answer.strip()
