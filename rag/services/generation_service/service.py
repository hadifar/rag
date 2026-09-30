from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph


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

    async def stream_events[E](
        self,
        graph: CompiledStateGraph,
        messages: list[BaseMessage],
        config: RunnableConfig,
        parse: Callable[[Mapping[str, Any]], E | None],
    ) -> AsyncIterator[E]:
        """Runs `graph` on `messages` and yields what `parse` makes of each of its raw
        stream events; events it returns None for are skipped.
        What the events mean is the caller's business, not generation's.
        """
        async for raw_event in graph.astream_events(
            {"messages": messages}, config=config, version="v2"
        ):
            event = parse(raw_event)
            if event is not None:
                yield event
