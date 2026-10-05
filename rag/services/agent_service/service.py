from collections.abc import Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel

from rag.domain.models import RunContext, ToolAgentSpec
from rag.services.agent_service.agent import Agent
from rag.services.agent_service.builder import build_tool_agent
from rag.shared.resilience import or_default


class AgentService:
    """The only holder of the LLM, and the only place LangChain is used: single-shot
    generation, and the agents built on the model.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None, RunContext | None], RunnableConfig],
        retry_attempts: int,  # tries per LLM call before an agent's turn fails or a guard falls back
    ):
        self._llm = llm
        self._checkpointer = checkpointer
        self._trace_config = trace_config
        self._retry_attempts = retry_attempts

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        llm = self._llm.with_retry(stop_after_attempt=attempts)
        return (await llm.ainvoke(prompt)).text

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class)"""
        llm = self._llm.with_structured_output(schema).with_retry(
            stop_after_attempt=attempts
        )
        # Its own trace only if named: inside an agent's run, a config of its own would
        # cut the call from the run's trace.
        config = self._trace_config(trace, ctx) if trace is not None else None
        return cast(T, await llm.ainvoke(prompt, config=config))

    def create_agent(self, spec: ToolAgentSpec) -> Agent:
        """A chat agent built as `spec` describes"""

        graph = build_tool_agent(
            self._llm, spec, self._judge, self._checkpointer, self._retry_attempts
        )

        return Agent(graph, self._checkpointer, self._trace_config)

    async def _judge[T: BaseModel](self, prompt: str, schema: type[T]) -> T | None:
        """The guards' LLM call (a `Judge`): retried, and if it still fails, None, which
        neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate_structured(prompt, schema, attempts=self._retry_attempts),
            None,
        )
