from pydantic import BaseModel, Field, field_validator

from rag.domain.errors import BlankTitleError

TITLE_PROMPT = (
    "Write a title for a support conversation that starts with the message below.\n\n"
    "USER:\n{message}"
)
# Only the start of the message is needed to title it; caps the title call's cost.
TITLE_MESSAGE_EXCERPT = 1000
MAX_TITLE_LENGTH = 80  # cap on an LLM-written title
FALLBACK_TITLE_LENGTH = (
    60  # the title cut from the message when the LLM can't write one
)


class TitleOutput(BaseModel):
    """The LLM's title, tidied on the way in: trimmed and capped in length, and a blank
    one is rejected (`BlankTitleError`), so a `TitleOutput` always holds a usable title.
    """

    title: str = Field(description="At most 6 words, no quotes and no trailing period.")

    @field_validator("title")
    @classmethod
    def _tidy(cls, title: str) -> str:
        title = title.strip()[:MAX_TITLE_LENGTH]
        if not title:
            raise BlankTitleError
        return title


def title_prompt(message: str) -> str:
    return TITLE_PROMPT.format(message=message[:TITLE_MESSAGE_EXCERPT])


def fallback_title(message: str) -> str:
    title = " ".join(message.split())
    if len(title) <= FALLBACK_TITLE_LENGTH:
        return title
    return title[: FALLBACK_TITLE_LENGTH - 1].rstrip() + "…"
