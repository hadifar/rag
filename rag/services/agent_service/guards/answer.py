from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage

from rag.domain.models import AnswerVerdict, AttachmentFile
from rag.domain.ports import LLMPort
from rag.services.agent_service.attachments import attachments_of, text_of
from rag.services.agent_service.prompts import ANSWER_GUARD_PROMPT
from rag.services.agent_service.tools import SKILL_TOOLS
from rag.services.agent_service.messages import current_turn, turn_tool_messages
from rag.shared.resilience import or_default


@dataclass(frozen=True)
class AnswerCheck:
    """The turn's answer and the context it is to be grounded in."""

    context: str
    answer: str

    async def passes(self, llm: LLMPort) -> bool:
        """Whether the answer is supported by the context; True if the guard's
        LLM call failed (fail open).
        """
        prompt = ANSWER_GUARD_PROMPT.format(context=self.context, answer=self.answer)
        verdict = await or_default(llm.generate_structured(prompt, AnswerVerdict), None)
        return verdict is None or verdict.grounded


def _collect_context(messages: Sequence[BaseMessage]) -> str:
    return "\n\n".join(
        str(m.content)
        for m in turn_tool_messages(messages)
        if m.content and m.name not in SKILL_TOOLS
    )


def has_context(messages: Sequence[BaseMessage]) -> bool:
    """Whether the turn retrieved anything for its answer to be checked against."""
    return bool(_collect_context(messages))


def answer_to_check(
    answer: AIMessage,
    messages: Sequence[BaseMessage],
    files: Mapping[str, AttachmentFile],
) -> AnswerCheck | None:
    """`answer`, against the turn's retrieved context (in `messages`) and the text the
    user attached to their question (among `files`, by id); None if there's nothing
    to check.
    """
    context = _collect_context(messages)

    # .text, not .content: under the Responses API content is a list of blocks,
    # reasoning included, and only the answer's text is to be checked.
    if not context or not answer.text:
        # Nothing was retrieved this turn (e.g. small talk) — nothing to check against.
        return None
    question = current_turn(messages)[0]
    if attached := text_of(attachments_of(question, files)):
        context = f"{context}\n\nATTACHED BY THE USER:\n{attached}"
    return AnswerCheck(context, answer.text)
