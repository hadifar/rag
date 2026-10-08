import uuid

from langchain_core.runnables import RunnableConfig

from rag.adapters.langchain.llm_client import build_llms
from rag.container import build_container
from rag.domain.models import RunContext, TextDelta, ToolCall
from rag.repository.cache_repository import NoCache
from rag.services.agent_service.agent import RagAgent
from rag.services.agent_service.llm import Llm
from tests.unit.fakes import FakeSkillRepository


def _no_tracing(name: str | None, ctx: RunContext | None) -> RunnableConfig:
    return {}


async def _ask(integration_settings, message: str) -> tuple[str, list[str]]:
    async with build_container(integration_settings) as container:
        # The agent alone, over the app's search: through `chat_service`, the turn
        # would need a real user and conversation.
        llm = Llm(
            build_llms(integration_settings),
            _no_tracing,
            attempts=integration_settings.LLM.RETRY_ATTEMPTS,
        )
        agent = RagAgent(
            llm,
            search=container.retrieval_service,
            skills=FakeSkillRepository(),  # a throwaway user has none
            verdicts=NoCache(),
        )
        answer = ""
        tool_calls = []

        ctx = RunContext(user_id=uuid.uuid4(), conversation_id=uuid.uuid4())
        async for event in agent.stream(message, [], ctx):
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
