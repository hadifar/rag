from typing import cast

from langchain_core.runnables import Runnable

from rag.services.completion_service.service import CompletionService
from tests.unit.fakes import FakeTitleModel


def _service(model: FakeTitleModel) -> CompletionService:
    return CompletionService(cast(Runnable, model))


async def test_title_is_the_first_line_without_quotes_or_trailing_period() -> None:
    model = FakeTitleModel(reply='"Password reset."\nextra line')

    title = await _service(model).generate_title("question", "answer")

    assert title == "Password reset"


async def test_title_prompt_sees_both_sides_of_the_exchange() -> None:
    model = FakeTitleModel()

    await _service(model).generate_title("How do I reset?", "Click reset.")

    assert "How do I reset?" in model.prompts[0]
    assert "Click reset." in model.prompts[0]


async def test_failed_title_generation_returns_none() -> None:
    model = FakeTitleModel(error=RuntimeError("LLM down"))

    assert await _service(model).generate_title("question", "answer") is None


async def test_blank_reply_returns_none() -> None:
    model = FakeTitleModel(reply="  \n ")

    assert await _service(model).generate_title("question", "answer") is None
