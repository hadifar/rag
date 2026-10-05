from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    hook_config,
)
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel

from rag.services.agent_service.middleware.judge import Judge
from rag.services.agent_service.prompts import (
    REVISION_INSTRUCTION,
    VERIFIER_PROMPT,
)
from rag.services.agent_service.streaming import ANSWER_VERIFICATION
from rag.services.agent_service.turn import (
    current_turn,
    is_final_answer,
    turn_tool_messages,
)


def _collect_context(
    messages: Sequence[BaseMessage], unverified_tools: frozenset[str]
) -> str:
    return "\n\n".join(
        str(m.content)
        for m in turn_tool_messages(messages)
        if m.content and m.name not in unverified_tools
    )


def _verification_inputs(
    messages: Sequence[BaseMessage], unverified_tools: frozenset[str]
) -> tuple[str, str] | None:
    """The turn's retrieved context and the answer to check against it; None if there's
    nothing to check.
    """
    context = _collect_context(messages, unverified_tools)
    answer = messages[-1]

    # .text, not .content: under the Responses API content is a list of blocks,
    # reasoning included, and only the answer's text is to be verified.
    if not context or not isinstance(answer, AIMessage) or not answer.text:
        # Nothing was retrieved this turn (e.g. small talk) — nothing to verify against.
        return None
    return context, answer.text


class GroundednessVerdict(BaseModel):
    grounded: bool


async def is_grounded(judge: Judge, context: str, answer: str) -> bool:
    """Whether `answer` is supported by `context`; True if the verifier failed."""
    prompt = VERIFIER_PROMPT.format(context=context, answer=answer)
    verdict = await judge(prompt, GroundednessVerdict)
    return verdict is None or verdict.grounded


def _turn_answers(messages: Sequence[BaseMessage]) -> list[AIMessage]:
    """This turn's final answers, oldest first. A rejected answer stays in the thread
    when the model is sent back to revise, so every answer but the last was rejected.
    """
    return [m for m in current_turn(messages) if is_final_answer(m)]


class GroundednessGuard(AgentMiddleware):
    """Checks each final answer against this turn's retrieved context; if it isn't
    supported, sends the model back to revise, up to `max_revisions` times per turn.
    The results of `unverified_tools` (ones about the user, not the product, e.g.
    saving a preference) aren't context to check against.
    The stream holds a checked answer back until its verdict (`AnswerGate`), so a
    rejected answer never reaches the user. The revision instruction is added to that
    model call only, never saved to the thread. Revisions are counted from this turn's
    messages, so no state carries over between turns.
    """

    def __init__(
        self,
        judge: Judge,
        max_revisions: int,
        unverified_tools: frozenset[str] = frozenset(),
    ):
        super().__init__()
        self._judge = judge
        self._max_revisions = max_revisions
        self._unverified_tools = unverified_tools

    @hook_config(can_jump_to=["model"])
    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        if not is_final_answer(state["messages"][-1]):
            return None  # Not a final answer yet: the model is still searching.

        revisions = len(_turn_answers(state["messages"])) - 1

        if revisions >= self._max_revisions:
            return None

        inputs = _verification_inputs(state["messages"], self._unverified_tools)
        if inputs is None:
            return None

        # The check is a whole LLM call the answer is held back for: the client shows it.
        await adispatch_custom_event(ANSWER_VERIFICATION, {"status": "pending"})
        grounded = await is_grounded(self._judge, *inputs)
        await adispatch_custom_event(
            ANSWER_VERIFICATION, {"status": "done", "grounded": grounded}
        )
        return None if grounded else {"jump_to": "model"}

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        # The model only runs right after a final answer when after_model rejected it.
        last = request.messages[-1] if request.messages else None
        if is_final_answer(last):
            request = request.override(
                messages=[*request.messages, HumanMessage(content=REVISION_INSTRUCTION)]
            )
        return await handler(request)
