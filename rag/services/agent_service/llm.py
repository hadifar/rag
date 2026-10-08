from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

from rag.domain.models import (
    DEFAULT_MODEL,
    AttachmentFile,
    Effort,
    ModelName,
    RunContext,
)
from rag.services.agent_service.attachments import render

TraceConfig = Callable[[str | None, RunContext | None], RunnableConfig]


class Llm:
    """The LLM (an LLMPort): the one holder of the models, with their tracing and
    retries."""

    def __init__(
        self,
        models: Mapping[ModelName, BaseChatModel],
        trace_config: TraceConfig,
        attempts: int,
        *,
        reasoning: bool = False,
    ):
        self.models = dict(models)
        self.model = self.models[DEFAULT_MODEL]
        self.trace_config = trace_config
        self._attempts = attempts  # tries per call
        self._reasoning = reasoning  # the models think (LLM__REASONING_EFFORT is set)

    def prepare(self, model: Runnable[Any, Any], effort: Effort) -> Runnable[Any, Any]:
        """`model`, retried like every other call and set to think as hard as `effort`
        says (if it reasons).
        """
        if self._reasoning:
            model = model.bind(reasoning={"effort": effort, "summary": "auto"})
        return model.with_retry(stop_after_attempt=self._attempts)

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attachments: Sequence[AttachmentFile] = (),
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), of
        `prompt` and then its `attachments`.
        """
        llm = self.model.with_structured_output(schema).with_retry(
            stop_after_attempt=self._attempts
        )
        # Its own trace only if named: inside an agent's run, a config of its own would
        # cut the call from the run's trace.
        config = self.trace_config(trace, ctx) if trace is not None else None
        request: LanguageModelInput = prompt
        if attachments:
            text = {"type": "text", "text": prompt}
            request = [HumanMessage([text, *(render(f) for f in attachments)])]
        return cast(T, await llm.ainvoke(request, config=config))
