from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, Any, NotRequired

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.agents.middleware.types import PrivateStateAttr
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from rag.domain.prompts import (
    GUARDRAIL_PROMPT,
    OFF_TOPIC_INSTRUCTION,
)

Classify = Callable[[str], Awaitable[str]]  # a prompt in, the LLM's reply text out


def _latest_human_message(messages: Sequence[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage) and message.content:
            return str(message.content)
    return ""


async def is_relevant(classify: Classify, messages: Sequence[BaseMessage]) -> bool:
    message = _latest_human_message(messages)
    if not message:
        return True

    verdict = await classify(GUARDRAIL_PROMPT.format(message=message))
    return "IRRELEVANT" not in verdict.upper()


class TopicalState(AgentState):
    off_topic: NotRequired[Annotated[bool, PrivateStateAttr]]


class TopicalGuard(AgentMiddleware[TopicalState]):
    """Classifies each user message once per turn; for an off-topic one, the model is
    told to decline and gets no tools. The instruction is added to that model call
    only, never saved to the thread, so it can't leak into later turns.
    """

    state_schema = TopicalState

    def __init__(self, classifier: Classify):
        super().__init__()
        self._classifier = classifier

    async def abefore_agent(
        self, state: TopicalState, runtime: Runtime
    ) -> dict[str, Any] | None:
        # Written every turn, so the previous turn's verdict never carries over.
        return {"off_topic": not await is_relevant(self._classifier, state["messages"])}

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        if request.state.get("off_topic"):
            base = request.system_message.text if request.system_message else ""
            request = request.override(
                system_message=SystemMessage(
                    content=f"{base}\n\n{OFF_TOPIC_INSTRUCTION}"
                ),
                tools=[],
            )
        return await handler(request)
