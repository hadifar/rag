import logging
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any, cast, overload

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class GenerationService:
    """The only holder of the LLM: everything that needs a model goes through here."""

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    @overload
    async def generate(self, prompt: str, *, attempts: int = 1) -> str: ...
    @overload
    async def generate[F](
        self,
        prompt: str,
        *,
        attempts: int = 1,
        fallback: F,
    ) -> str | F: ...
    @overload
    async def generate[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
    ) -> T: ...
    @overload
    async def generate[T: BaseModel, F](
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
        fallback: F,
    ) -> T | F: ...
    async def generate(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
        *,
        attempts: int = 1,
        fallback: Any = ...,
    ) -> Any:
        """One-shot completion, tried up to `attempts` times. With a `schema` (a Pydantic
        model class) the reply is enforced to fit it and comes back as an instance;
        without one, as plain text. If it fails (LLM error, a reply the schema rejects)
        it raises, unless a `fallback` is given: then it logs and returns that instead.
        To bound the time, wrap the call in `asyncio.timeout`; that too then raises.
        """
        try:
            return await self._complete(prompt, schema, attempts)
        except Exception:
            if fallback is ...:
                raise
            logger.warning("LLM call failed; using the fallback", exc_info=True)
            return fallback

    async def _complete(
        self, prompt: str, schema: type[BaseModel] | None, attempts: int
    ) -> str | BaseModel:
        if schema is None:
            reply = await self._llm.with_retry(stop_after_attempt=attempts).ainvoke(
                prompt
            )
            return reply.text
        structured = self._llm.with_structured_output(schema)
        reply = await structured.with_retry(stop_after_attempt=attempts).ainvoke(prompt)
        return cast(BaseModel, reply)

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
