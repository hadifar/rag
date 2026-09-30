from typing import cast

from langchain_core.runnables import Runnable

from rag.services.generation_service.service import GenerationService
from tests.unit.fakes import FakeTitleModel


def _service(model: FakeTitleModel) -> GenerationService:
    return GenerationService(cast(Runnable, model))


async def test_title_is_the_first_line_without_quotes_or_trailing_period() -> None:
    model = FakeTitleModel(reply='"Password reset."\nextra line')

    title = await _service(model).generate_title("question")

    assert title == "Password reset"


async def test_title_prompt_sees_the_first_message() -> None:
    model = FakeTitleModel()

    await _service(model).generate_title("How do I reset?")

    assert "How do I reset?" in model.prompts[0]


async def test_failed_title_generation_returns_none() -> None:
    model = FakeTitleModel(error=RuntimeError("LLM down"))

    assert await _service(model).generate_title("question") is None


async def test_blank_reply_returns_none() -> None:
    model = FakeTitleModel(reply="  \n ")

    assert await _service(model).generate_title("question") is None
