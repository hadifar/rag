import asyncio
import logging

from langchain_core.runnables import Runnable

from rag.services.generation_service.prompts import TITLE_PROMPT

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 80
# Only the start of the message is needed to title it; caps the title call's cost.
TITLE_MESSAGE_EXCERPT = 1000
# The client waits on this for the sidebar title; don't hold it on a slow LLM.
TITLE_TIMEOUT_SECONDS = 10


class GenerationService:
    def __init__(self, llm: Runnable):
        self._llm = llm

    async def generate_title(self, message: str) -> str | None:
        """An LLM-written title, or None to keep the fallback. Never raises: a failed
        title must not fail the turn the user already got an answer for.
        """
        prompt = TITLE_PROMPT.format(message=message[:TITLE_MESSAGE_EXCERPT])
        try:
            async with asyncio.timeout(TITLE_TIMEOUT_SECONDS):
                reply = await self._llm.ainvoke(prompt)
        except Exception:
            logger.warning(
                "Title generation failed; keeping the fallback", exc_info=True
            )
            return None
        return _clean_title(str(reply.content))


def _clean_title(raw: str) -> str | None:
    first_line = next(iter(raw.strip().splitlines()), "")
    title = first_line.strip().strip("\"'`").strip().rstrip(".")
    return title[:MAX_TITLE_LENGTH] or None
