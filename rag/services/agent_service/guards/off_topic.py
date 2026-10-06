import logging
from collections.abc import Sequence
from langchain_core.messages import BaseMessage

from rag.domain.models import InputDecision, InputVerdict
from rag.domain.ports import CachePort, LLMPort
from rag.services.agent_service.prompts import GUARDRAIL_PROMPT, OFF_TOPIC_SCOPE
from rag.services.agent_service.turn import is_final_answer, split_turns
from rag.shared.resilience import or_default

logger = logging.getLogger(__name__)

# Earlier turns the classifier sees, to read a follow-up like "and what about pricing?".
HISTORY_TURNS = 2


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
    llm: LLMPort,
    messages: Sequence[BaseMessage],
    cache: CachePort[InputVerdict],
) -> InputDecision:
    """The decision for the latest user message, with the turns before it for context;
    allow if there's none or the classifier failed (fail open). Verdicts are cached by
    the whole prompt, so the same message after a different history is classified
    afresh; a fail-open allow is never cached.
    """
    turns = split_turns(messages)
    if not turns or not (message := turns[-1][0].text):
        return "allow"

    prompt = GUARDRAIL_PROMPT.format(
        scope=OFF_TOPIC_SCOPE, history=_history(turns[:-1]), message=message
    )
    verdict = await or_default(cache.get(prompt), None)
    if verdict is None:
        verdict = await or_default(llm.generate_structured(prompt, InputVerdict), None)
        if verdict is None:
            return "allow"
        await or_default(cache.put(prompt, verdict), None)
    if verdict.decision == "block":
        logger.info("Blocked a chat message: %s", verdict.reason)
    return verdict.decision
