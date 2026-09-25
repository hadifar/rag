import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from rag.config import LangfuseObservability, LoggingObservability, Settings

logger = logging.getLogger(__name__)

TraceConfig = Callable[[str | None], RunnableConfig]


class _LoggingCallbackHandler(BaseCallbackHandler):
    """LangChain callback: it's a drop-in trace_config backend with zero extra infra."""

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        logger.info("llm_start", extra={"run_id": str(kwargs.get("run_id"))})

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.info("llm_end", extra={"run_id": str(kwargs.get("run_id"))})

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        logger.info("tool_start", extra={"tool": serialized.get("name")})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        logger.info("tool_end", extra={"output": str(output)})


def _logging_trace_config(name: str | None = None) -> RunnableConfig:
    config: RunnableConfig = {"callbacks": [_LoggingCallbackHandler()]}
    if name is not None:
        config["run_name"] = name
    return config


@asynccontextmanager
async def _open_logging(config: LoggingObservability) -> AsyncGenerator[TraceConfig]:
    yield _logging_trace_config


@asynccontextmanager
async def _open_langfuse(config: LangfuseObservability) -> AsyncGenerator[TraceConfig]:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    Langfuse(
        public_key=config.PUBLIC_KEY.get_secret_value(),
        secret_key=config.SECRET_KEY.get_secret_value(),
        host=config.HOST,
    )
    handler = CallbackHandler()

    def trace_config(name: str | None = None) -> RunnableConfig:
        cfg: RunnableConfig = {"callbacks": [handler]}
        if name is not None:
            cfg["run_name"] = name
        return cfg

    try:
        yield trace_config
    finally:
        from langfuse import get_client

        get_client().flush()


@asynccontextmanager
async def open_trace_config(settings: Settings) -> AsyncGenerator[TraceConfig]:
    match settings.OBSERVABILITY:
        case LoggingObservability() as config:
            async with _open_logging(config) as trace_config:
                yield trace_config
        case LangfuseObservability() as config:
            async with _open_langfuse(config) as trace_config:
                yield trace_config
