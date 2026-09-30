from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel


class GenerationService:
    """The only holder of the LLM: everything that needs a model goes through here."""

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        llm = self._llm.with_retry(stop_after_attempt=attempts)
        return (await llm.ainvoke(prompt)).text

    async def generate_structured[T: BaseModel](
        self, prompt: str, schema: type[T], *, attempts: int = 1
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), as an
        instance of it; raises if all `attempts` fail or the reply is rejected.
        """
        llm = self._llm.with_structured_output(schema).with_retry(
            stop_after_attempt=attempts
        )
        return cast(T, await llm.ainvoke(prompt))

    def create_agent(
        self,
        tools: list[BaseTool],
        system_prompt: str,
        middleware: list[AgentMiddleware[Any, Any]],
        checkpointer: BaseCheckpointSaver,
    ) -> CompiledStateGraph:
        """A tool-calling agent graph on the model, saving its threads to `checkpointer`."""
        return create_agent(
            self._llm,
            tools,
            system_prompt=system_prompt,
            middleware=middleware,
            checkpointer=checkpointer,
        )

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
