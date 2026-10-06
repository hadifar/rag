from collections.abc import Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from rag.domain.models import RunContext

TraceConfig = Callable[[str | None, RunContext | None], RunnableConfig]


class Llm:
    """The LLM (an LLMPort): the one holder of the model, with its tracing and retries.
    Others get single-shot structured generation from it; the agent also binds its
    tools to `model`.
    """

    def __init__(self, model: BaseChatModel, trace_config: TraceConfig, attempts: int):
        self.model = model
        self.trace_config = trace_config
        self.attempts = attempts  # tries per call

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class)"""
        llm = self.model.with_structured_output(schema).with_retry(
            stop_after_attempt=self.attempts
        )
        # Its own trace only if named: inside an agent's run, a config of its own would
        # cut the call from the run's trace.
        config = self.trace_config(trace, ctx) if trace is not None else None
        return cast(T, await llm.ainvoke(prompt, config=config))
