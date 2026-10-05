import uuid
from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel

from rag.domain.models import RunContext, StreamEvent, ToolAgentSpec


class ChatAgentPort(Protocol):
    def stream(self, message: str, ctx: RunContext) -> AsyncIterator[StreamEvent]:
        """Answers `message` in `ctx`'s conversation for its user, remembering the turn
        for the next: the answer's events as they happen, then the turn's references if
        it searched.
        """
        ...

    async def forget(self, conversation_id: uuid.UUID) -> None:
        """Drops what the agent remembers of the conversation (its messages)."""
        ...


class AgentServicePort(Protocol):
    """The LLM: single-shot generation and the agents built on it, so nothing else ever
    holds the model or touches LangChain.
    """

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        ...

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), as an
        instance of it; raises if all `attempts` fail or the reply is rejected. `trace`
        names and tags the call as a trace of its own, under `ctx`'s user and
        conversation; leave it out inside an agent's run, whose trace already has it.
        """
        ...

    def create_agent(self, spec: ToolAgentSpec) -> ChatAgentPort:
        """A chat agent built as `spec` describes; raises ValueError if two of its
        tools share a name.
        """
        ...
