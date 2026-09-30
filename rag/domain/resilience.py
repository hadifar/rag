import logging
from collections.abc import Awaitable

logger = logging.getLogger(__name__)


async def or_default[T, D](awaitable: Awaitable[T], default: D) -> T | D:
    """What `awaitable` gives, or `default` if it raises (the failure is logged). For
    steps whose failure must not fail the caller, like a title or a guard's verdict.
    """
    try:
        return await awaitable
    except Exception:
        logger.warning("Failed; using the default", exc_info=True)
        return default
