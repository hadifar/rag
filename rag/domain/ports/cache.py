from typing import Protocol


class CachePort[T](Protocol):
    """Values of type T kept by the text they were computed from, each for a while.
    Either call may raise; a caller treats that as a miss, so a cache never fails it.
    """

    async def get(self, key: str) -> T | None:
        """The value kept for `key`, or None if there's none or it expired."""
        ...

    async def put(self, key: str, value: T) -> None: ...
