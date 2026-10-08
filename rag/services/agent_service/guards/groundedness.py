from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from rag.domain.ports import LLMPort
from rag.services.agent_service.prompts import VERIFIER_PROMPT
from rag.services.agent_service.skills import SKILL_TOOLS
from rag.services.agent_service.messages import turn_tool_messages
from rag.shared.resilience import or_default


class GroundednessVerdict(BaseModel):
    grounded: bool


def _collect_context(messages: Sequence[BaseMessage]) -> str:
    return "\n\n".join(
        str(m.content)
        for m in turn_tool_messages(messages)
        if m.content and m.name not in SKILL_TOOLS
    )


def verification_inputs(
    messages: Sequence[BaseMessage], attached: str = ""
) -> tuple[str, str] | None:
    """The turn's retrieved context, with the text the user `attached` to their
    message, and the answer to check against it; None if there's nothing to check.
    """
    context = _collect_context(messages)
    answer = messages[-1]

    # .text, not .content: under the Responses API content is a list of blocks,
    # reasoning included, and only the answer's text is to be verified.
    if not context or not isinstance(answer, AIMessage) or not answer.text:
        # Nothing was retrieved this turn (e.g. small talk) — nothing to verify against.
        return None
    if attached:
        context = f"{context}\n\nATTACHED BY THE USER:\n{attached}"
    return context, answer.text


async def is_grounded(
    llm: LLMPort,
    context: str,
    answer: str,
) -> bool:
    """Whether `answer` is supported by `context`; True if the verifier failed (fail
    open).
    """
    prompt = VERIFIER_PROMPT.format(context=context, answer=answer)
    verdict = await or_default(
        llm.generate_structured(prompt, GroundednessVerdict), None
    )
    return verdict is None or verdict.grounded
