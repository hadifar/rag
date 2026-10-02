from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage

from rag.domain.models import Capability, RunContext


class CapabilityInstructions(AgentMiddleware[AgentState, RunContext]):
    """Adds each capability's instructions to every model call's system message, read
    fresh for each call from the turn's RunContext, so what a tool changed mid-turn
    applies from the next call on. Added to the call only, never saved to the thread.
    """

    def __init__(self, capabilities: list[Capability]):
        super().__init__()
        self._instructions = [c.instructions for c in capabilities if c.instructions]

    async def awrap_model_call(
        self,
        request: ModelRequest[RunContext],
        handler: Callable[[ModelRequest[RunContext]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        ctx = request.runtime.context
        texts = [text for read in self._instructions if (text := await read(ctx))]
        if texts:
            base = request.system_message.text if request.system_message else ""
            request = request.override(
                system_message=SystemMessage(content="\n\n".join([base, *texts]))
            )
        return await handler(request)
