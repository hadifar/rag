from typing import Protocol

from pydantic import BaseModel


class Judge(Protocol):
    """The guards' LLM call: a prompt in, the reply parsed into `schema` out. Raises if
    the call fails; each guard decides what a failure means (both fail open).
    """

    async def __call__[T: BaseModel](self, prompt: str, schema: type[T]) -> T: ...
