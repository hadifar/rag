from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel

from rag.domain.agents import AgentSpec, Tool, ToolPort
from rag.domain.events import StreamEvent


class ChatAgentPort(Protocol):
    def stream(self, message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        """Answers `message` in the thread, saving the turn to it: the answer's events
        as they happen, then the turn's sources if it searched.
        """
        ...


class AgentServicePort(Protocol):
    """The LLM: single-shot generation, and the tools and agents built on it, so
    nothing else ever holds the model or touches LangChain.
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

    def create_tools(self, tools: list[Tool]) -> list[ToolPort]:
        """Each tool, ready for an agent; raises ValueError if two share a name."""
        ...

    def create_agent(self, spec: AgentSpec) -> ChatAgentPort:
        """A chat agent built as `spec` describes."""
        ...
