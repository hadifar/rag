import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from rag.config import LangfuseObservabilityConfig, LoggingObservabilityConfig, Settings
from rag.domain.models import RunContext

logger = logging.getLogger(__name__)

TraceConfig = Callable[[str | None, RunContext | None], RunnableConfig]


def _run_config(
    handler: BaseCallbackHandler, name: str | None, ctx: RunContext | None
) -> RunnableConfig:
    """A run traced by `handler`: named and tagged `name`, and given `ctx`, under its
    user and with its conversation as the session (the keys Langfuse reads).
    """
    config: RunnableConfig = {"callbacks": [handler]}
    if name is not None:
        config["run_name"] = name
        config["tags"] = [name]
    if ctx is not None:
        config["metadata"] = {
            "langfuse_user_id": str(ctx.user_id),
            "langfuse_session_id": str(ctx.conversation_id),
        }
    return config


class _LoggingCallbackHandler(BaseCallbackHandler):
    """LangChain callback: it's a drop-in trace_config backend with zero extra infra."""

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        logger.info("llm_start", extra={"run_id": str(kwargs.get("run_id"))})

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.info("llm_end", extra={"run_id": str(kwargs.get("run_id"))})

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        logger.info("tool_start", extra={"tool": serialized.get("name")})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        logger.info("tool_end", extra={"output": str(output)})


def _logging_trace_config(
    name: str | None = None, ctx: RunContext | None = None
) -> RunnableConfig:
    return _run_config(_LoggingCallbackHandler(), name, ctx)


@asynccontextmanager
async def _open_logging(
    config: LoggingObservabilityConfig,
) -> AsyncGenerator[TraceConfig, None]:
    yield _logging_trace_config


@asynccontextmanager
async def _open_langfuse(
    config: LangfuseObservabilityConfig,
) -> AsyncGenerator[TraceConfig, None]:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    Langfuse(
        public_key=config.PUBLIC_KEY.get_secret_value(),
        secret_key=config.SECRET_KEY.get_secret_value(),
        host=config.HOST,
    )
    handler = CallbackHandler()

    def trace_config(
        name: str | None = None, ctx: RunContext | None = None
    ) -> RunnableConfig:
        return _run_config(handler, name, ctx)

    try:
        yield trace_config
    finally:
        from langfuse import get_client

        get_client().flush()


@asynccontextmanager
async def open_trace_config(settings: Settings) -> AsyncGenerator[TraceConfig, None]:
    match settings.OBSERVABILITY:
        case LoggingObservabilityConfig() as config:
            async with _open_logging(config) as trace_config:
                yield trace_config
        case LangfuseObservabilityConfig() as config:
            async with _open_langfuse(config) as trace_config:
                yield trace_config
