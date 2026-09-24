from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from rag.config import get_settings

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langfuse.langchain import CallbackHandler


@lru_cache(maxsize=1)
def _handler() -> CallbackHandler | None:
    """Build a single Langfuse LangChain callback handler, or None when tracing
    is disabled. Initializing the Langfuse client wires up the global singleton
    that the handler (and ``flush()``) reuse.
    """
    settings = get_settings()
    if not settings.LANGFUSE_ENABLED:
        return None

    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY.get_secret_value(),
        secret_key=settings.LANGFUSE_SECRET_KEY.get_secret_value(),
        host=settings.LANGFUSE_HOST,
    )
    return CallbackHandler()


def trace_config(name: str | None = None) -> RunnableConfig:
    """LangChain ``config`` that routes a run to Langfuse when tracing is on.

    Returns ``{}`` when Langfuse is not configured, so callers can always pass
    ``config=trace_config(...)`` to ``.invoke()`` with no behavioral change.
    """
    handler = _handler()
    if handler is None:
        return {}
    config: RunnableConfig = {"callbacks": [handler]}
    if name is not None:
        config["run_name"] = name
    return config


def flush() -> None:
    """Flush buffered traces — call on shutdown so short-lived runs aren't lost."""
    if not get_settings().LANGFUSE_ENABLED:
        return
    from langfuse import get_client

    get_client().flush()
