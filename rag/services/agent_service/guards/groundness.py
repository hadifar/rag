from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    hook_config,
)
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import Runnable
from langgraph.runtime import Runtime

from rag.services.agent_service.turn import (
    current_turn,
    is_final_answer,
    turn_tool_messages,
)

VERIFIER_PROMPT = (
    "You are a strict fact-checker. Given the CONTEXT and an ANSWER, decide whether every "
    "factual claim in the ANSWER is supported by the CONTEXT. Reply with exactly one word: "
    "GROUNDED if fully supported, or UNGROUNDED otherwise.\n\n"
    "CONTEXT:\n{context}\n\nANSWER:\n{answer}"
)

REVISION_INSTRUCTION = (
    "Your previous answer wasn't fully supported by the retrieved context. Revise it (e.g., by rephrasing query) to "
    "state only what the context actually supports, or say you don't know."
)


def _collect_context(messages: Sequence[BaseMessage]) -> str:
    return "\n\n".join(
        str(m.content) for m in turn_tool_messages(messages) if m.content
    )


async def is_grounded(llm: Runnable, messages: Sequence[BaseMessage]) -> bool:
    context = _collect_context(messages)
    answer = messages[-1]

    if not context or not isinstance(answer, AIMessage) or not answer.content:
        # Nothing was retrieved this turn (e.g. small talk) — nothing to verify against.
        return True

    verdict = await llm.ainvoke(
        VERIFIER_PROMPT.format(context=context, answer=answer.content)
    )
    return "UNGROUNDED" not in str(verdict.content).upper()


def _turn_answers(messages: Sequence[BaseMessage]) -> list[AIMessage]:
    """This turn's final answers, oldest first. A rejected answer stays in the thread
    when the model is sent back to revise, so every answer but the last was rejected.
    """
    return [m for m in current_turn(messages) if is_final_answer(m)]


class GroundednessGuard(AgentMiddleware):
    """Checks each final answer against this turn's retrieved context; if it isn't
    supported, sends the model back to revise, up to `max_revisions` times per turn.
    The revision instruction is added to that model call only, never saved to the
    thread. Revisions are counted from this turn's messages, so no state carries over
    between turns.
    """

    def __init__(self, verifier: Runnable, max_revisions: int):
        super().__init__()
        self._verifier = verifier
        self._max_revisions = max_revisions

    @hook_config(can_jump_to=["model"])
    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        if not is_final_answer(state["messages"][-1]):
            return None  # Not a final answer yet: the model is still searching.

        revisions = len(_turn_answers(state["messages"])) - 1
        # Fail open past the cap: end the turn rather than loop, or make the user wait
        # on the LLM re-answering the same question indefinitely.
        if revisions >= self._max_revisions:
            return None
        if await is_grounded(self._verifier, state["messages"]):
            return None
        return {"jump_to": "model"}

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
