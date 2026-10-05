from typing import Protocol

from pydantic import BaseModel


class Judge(Protocol):
    """The guards' LLM call: a prompt in, the reply parsed into `schema` out; None if
    the call failed, which each guard reads as a pass (they fail open).
    """

    async def __call__[T: BaseModel](
        self, prompt: str, schema: type[T]
    ) -> T | None: ...
