from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from pydantic import BaseModel

from rag.domain.models import AgentMemory, RunContext, StreamEvent, ToolAgentSpec


class ChatTurnPort(Protocol):
    """A chat turn as it runs: iterate it for the answer's events. Once they end,
    `memory` is what the agent is to remember of the turn; None for one it is to
    forget (blocked, failed, or cut short by its caller).
    """

    def __aiter__(self) -> AsyncIterator[StreamEvent]: ...
    @property
    def memory(self) -> AgentMemory | None: ...


class RagServicePort(Protocol):
    def stream(
        self, message: str, history: Sequence[AgentMemory], ctx: RunContext
    ) -> ChatTurnPort:
        """Answers `message` in `ctx`'s conversation for its user, remembering
        `history`, the `memory` of each earlier turn, oldest first: the answer's events
        as they happen, then the turn's artifacts if a tool that hands any over ran.
        """
        ...


class LLMServicePort(Protocol):
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

    def create_agent(self, spec: ToolAgentSpec) -> RagServicePort:
        """A chat agent built as `spec` describes; raises ValueError if two of its
        tools share a name.
        """
        ...
