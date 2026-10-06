from collections.abc import Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from rag.domain.models import RunContext


class AgentService:
    """Single-shot structured generation on the LLM (an LLMServicePort), for the
    features outside the chat agent (titles, reranking).
    """

    def __init__(
        self,
        llm: BaseChatModel,
        trace_config: Callable[[str | None, RunContext | None], RunnableConfig],
    ):
        self._llm = llm
        self._trace_config = trace_config

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
