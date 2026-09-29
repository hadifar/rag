from typing import cast

from langchain_core.runnables import Runnable

from rag.services.generation_service.title import generate_title
from tests.unit.fakes import FakeTitleModel


async def test_title_is_the_first_line_without_quotes_or_trailing_period() -> None:
    model = FakeTitleModel(reply='"Password reset."\nextra line')

    title = await generate_title(cast(Runnable, model), "question", "answer")

    assert title == "Password reset"


async def test_title_prompt_sees_both_sides_of_the_exchange() -> None:
    model = FakeTitleModel()

    await generate_title(cast(Runnable, model), "How do I reset?", "Click reset.")

    assert "How do I reset?" in model.prompts[0]
    assert "Click reset." in model.prompts[0]


async def test_failed_title_generation_returns_none() -> None:
    model = FakeTitleModel(error=RuntimeError("LLM down"))

    assert await generate_title(cast(Runnable, model), "question", "answer") is None


async def test_blank_reply_returns_none() -> None:
    model = FakeTitleModel(reply="  \n ")

    assert await generate_title(cast(Runnable, model), "question", "answer") is None
