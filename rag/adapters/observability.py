import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from rag.config import Settings

logger = logging.getLogger(__name__)


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
async def _open_langfuse(
    settings: Settings,
) -> AsyncGenerator[Callable[[str | None], RunnableConfig]]:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    assert settings.LANGFUSE_PUBLIC_KEY is not None
    assert settings.LANGFUSE_SECRET_KEY is not None

    Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY.get_secret_value(),
        secret_key=settings.LANGFUSE_SECRET_KEY.get_secret_value(),
        host=settings.LANGFUSE_HOST,
    )
    handler = CallbackHandler()

    def trace_config(name: str | None = None) -> RunnableConfig:
        config: RunnableConfig = {"callbacks": [handler]}
        if name is not None:
            config["run_name"] = name
        return config

    try:
        yield trace_config
    finally:
        from langfuse import get_client

        get_client().flush()


@asynccontextmanager
async def open_trace_config(
    settings: Settings,
) -> AsyncGenerator[Callable[[str | None], RunnableConfig]]:

    match settings.OBSERVABILITY_BACKEND:
        case "logging":
            yield _logging_trace_config
        case "langfuse":
            async with _open_langfuse(settings) as trace_config:
                yield trace_config
