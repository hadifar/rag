from collections.abc import AsyncIterator

from langchain_core.language_models import BaseChatModel


class GenerationService:
    """The only holder of the LLM: everything that needs a model goes through here."""

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    @property
    def chat_model(self) -> BaseChatModel:
        """The model itself, for callers that build their own chat flow on it (tools,
        agents) rather than plain text generation.
        """
        return self._llm

    async def generate(self, prompt: str) -> str:
        """One-shot completion; raises if the LLM call fails."""
        reply = await self._llm.ainvoke(prompt)
        return reply.text

    async def stream(self, prompt: str) -> AsyncIterator[str]:

        async for chunk in self._llm.astream(prompt):
            if chunk.text:
                yield chunk.text
