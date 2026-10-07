from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from pydantic import BaseModel

from rag.domain.models import AgentMemory, AttachmentFile, RunContext, StreamEvent


class ChatTurnPort(Protocol):
    """A chat turn as it runs: iterate it for the answer's events. Once they end,
    `memory` is what the agent is to remember of the turn; None for one it is to
    forget (blocked, failed, or cut short by its caller).
    """

    def __aiter__(self) -> AsyncIterator[StreamEvent]: ...
    @property
    def memory(self) -> AgentMemory | None: ...


class AgentPort(Protocol):
    def stream(
        self,
        message: str,
        history: Sequence[AgentMemory],
        ctx: RunContext,
        *,
        attachments: Sequence[AttachmentFile] = (),
        earlier_attachments: Sequence[AttachmentFile] = (),
    ) -> ChatTurnPort:
        """Answers `message` and its `attachments` in `ctx`'s conversation for its
        user, remembering `history`, the `memory` of each earlier turn, oldest first:
        the answer's events as they happen, then the turn's artifacts if a tool that
        hands any over ran. `memory` refers to attachments by id only; the ones the
        earlier turns were sent with are `earlier_attachments`.
        """
        ...


class LLMPort(Protocol):
    """The LLM's single-shot generation, so nothing outside the agent service ever
    holds the model or touches LangChain.
    """

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        attachments: Sequence[AttachmentFile] = (),
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), as an
        instance of it; raises once its retries run out or the reply is rejected.
        `attachments` are sent after the prompt, as the model reads each kind. `trace`
        names and tags the call as a trace of its own, under `ctx`'s user and
        conversation; leave it out inside an agent's run, whose trace already has it.
        """
        ...
