import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, Any, Literal, NotRequired

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    hook_config,
)
from langchain.agents.middleware.types import PrivateStateAttr
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import BaseMessage, RemoveMessage
from langchain_core.tools import BaseTool
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from rag.services.agent_service.events import INPUT_BLOCKED
from rag.services.agent_service.middleware.instructions import with_instructions
from rag.services.agent_service.middleware.judge import Judge
from rag.services.agent_service.middleware.prompts import (
    BLOCKED_MESSAGE,
    GUARDRAIL_PROMPT,
    OFF_TOPIC_INSTRUCTION,
)
from rag.services.agent_service.turn import is_final_answer, split_turns
from rag.shared.resilience import or_default

logger = logging.getLogger(__name__)

# Earlier turns the classifier sees, to read a follow-up like "and what about pricing?".
HISTORY_TURNS = 2

Decision = Literal["allow", "restrict", "block"]


class InputVerdict(BaseModel):
    # Before the decision, so the model gives its reason before it decides.
    reason: str = Field(
        description="One sentence on why the message gets the decision."
    )
    decision: Decision


def _history(turns: Sequence[Sequence[BaseMessage]]) -> str:
    """Each turn's user message and the answer it got: no tool output, which is long
    and could carry text that steers the classifier.
    """
    lines: list[str] = []
    for turn in turns[-HISTORY_TURNS:]:
        lines.append(f"User: {turn[0].text}")
        # A rejected answer stays in the thread: the last one is what the user saw.
        if answers := [m for m in turn if is_final_answer(m)]:
            lines.append(f"Assistant: {answers[-1].text}")
    return "\n".join(lines) or "(none)"


async def classify_input(judge: Judge, messages: Sequence[BaseMessage]) -> Decision:
    """The decision for the latest user message; allow if there's none or the
    classifier failed.
    """
    turns = split_turns(messages)
    if not turns or not (message := turns[-1][0].text):
        return "allow"

    prompt = GUARDRAIL_PROMPT.format(history=_history(turns[:-1]), message=message)
    verdict = await or_default(judge(prompt, InputVerdict), None)
    if verdict is None:
        return "allow"
    if verdict.decision == "block":
        logger.info("Blocked a chat message: %s", verdict.reason)
    return verdict.decision


def _name(tool: BaseTool | dict[str, Any]) -> str | None:
    return tool.get("name") if isinstance(tool, dict) else tool.name


class OffTopicState(AgentState):
    off_topic: NotRequired[Annotated[bool, PrivateStateAttr]]


class OffTopicGuard(AgentMiddleware[OffTopicState]):
    """Classifies each user message once per turn, with the turns before it for context.
    Blocked (an injection, jailbreak or harmful request): the turn ends before the model
    runs, the user gets a fixed refusal, and the message is dropped from the thread so
    no later turn's model call sees it. Restricted (harmless but off-topic): the model
    is told to decline and gets no tools but `kept_tools` (ones about the user, not the
    product, e.g. saving a preference). The instruction is added to that model call
    only, never saved to the thread, so it can't leak into later turns.
    """

    state_schema = OffTopicState

    def __init__(self, judge: Judge, kept_tools: frozenset[str] = frozenset()):
        super().__init__()
        self._judge = judge
        self._kept_tools = kept_tools

    @hook_config(can_jump_to=["end"])
    async def abefore_agent(
        self, state: OffTopicState, runtime: Runtime
    ) -> dict[str, Any] | None:
        decision = await classify_input(self._judge, state["messages"])
        if decision == "block":
            await adispatch_custom_event(INPUT_BLOCKED, {"message": BLOCKED_MESSAGE})
            question = state["messages"][-1]
            # The thread's reducer gives every message an id.
            assert question.id is not None
            return {"messages": [RemoveMessage(id=question.id)], "jump_to": "end"}
        # Written every turn, so the previous turn's verdict never carries over.
        return {"off_topic": decision == "restrict"}

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        if request.state.get("off_topic"):
            request = with_instructions(request, OFF_TOPIC_INSTRUCTION).override(
                tools=[t for t in request.tools if _name(t) in self._kept_tools]
            )
        return await handler(request)
