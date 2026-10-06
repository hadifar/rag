import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from rag.services.agent_service.prompts import GUARDRAIL_PROMPT, OFF_TOPIC_SCOPE
from rag.services.agent_service.turn import is_final_answer, split_turns
from rag.shared.resilience import or_default

logger = logging.getLogger(__name__)

# Earlier turns the classifier sees, to read a follow-up like "and what about pricing?".
HISTORY_TURNS = 2

# allow: about the product. restrict: harmless but off-topic, so the model declines.
# block: an injection, jailbreak or harmful request, which never reaches the model.
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


async def classify_input(
    judge: Callable[[str, type[InputVerdict]], Awaitable[InputVerdict]],
    messages: Sequence[BaseMessage],
) -> Decision:
    """The decision for the latest user message, with the turns before it for context;
    allow if there's none or the classifier failed (fail open).
    """
    turns = split_turns(messages)
    if not turns or not (message := turns[-1][0].text):
        return "allow"

    prompt = GUARDRAIL_PROMPT.format(
        scope=OFF_TOPIC_SCOPE, history=_history(turns[:-1]), message=message
    )
    verdict = await or_default(judge(prompt, InputVerdict), None)
    if verdict is None:
        return "allow"
    if verdict.decision == "block":
        logger.info("Blocked a chat message: %s", verdict.reason)
    return verdict.decision
