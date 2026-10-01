from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel

from rag.domain.models import AgentSpec, HistoryMessage, StreamEvent


class ChatAgentPort(Protocol):
    def stream(self, message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        """Answers `message` in the thread, saving the turn to it: the answer's events
        as they happen, then the turn's sources if it searched.
        """
        ...


class AgentServicePort(Protocol):
    """The LLM: single-shot generation, the tools and agents built on it, and the
    threads they save, so nothing else ever holds the model or touches LangChain.
    """

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        ...

    async def generate_structured[T: BaseModel](
        self, prompt: str, schema: type[T], *, attempts: int = 1
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), as an
        instance of it; raises if all `attempts` fail or the reply is rejected.
        """
        ...

    def create_agent(self, spec: AgentSpec) -> ChatAgentPort:
        """A chat agent built as `spec` describes; raises ValueError if two of its
        tools share a name.
        """
        ...

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        """The thread's messages as the user saw them; empty for an unknown thread."""
        ...

    async def delete_history(self, thread_id: str) -> None: ...
    async def list_thread_ids(self) -> set[str]:
        """Every thread that has stored messages."""
        ...
