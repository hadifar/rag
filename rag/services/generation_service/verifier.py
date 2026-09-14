"""Groundedness check: does the final answer actually follow from the retrieved
context, or does it contain claims the search results don't support?

Reuses the retrieved context already sitting in message history (ToolMessage
content from the search_kb calls this turn) instead of threading it through
GraphState separately.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

VERIFIER_PROMPT = (
    "You are a strict fact-checker. Given the CONTEXT and an ANSWER, decide whether every "
    "factual claim in the ANSWER is supported by the CONTEXT. Reply with exactly one word: "
    "GROUNDED if fully supported, or UNGROUNDED otherwise.\n\n"
    "CONTEXT:\n{context}\n\nANSWER:\n{answer}"
)

REVISION_INSTRUCTION = (
    "Your previous answer wasn't fully supported by the retrieved context. Revise it to "
    "state only what the context actually supports, or say you don't know."
)


def _collect_context(messages: list[BaseMessage]) -> str:
    return "\n\n".join(
        str(m.content) for m in messages if isinstance(m, ToolMessage) and m.content
    )


async def is_grounded(llm: BaseChatModel, messages: list[BaseMessage]) -> bool:
    context = _collect_context(messages)
    answer = messages[-1]

    if not context or not isinstance(answer, AIMessage) or not answer.content:
        # Nothing was retrieved this turn (e.g. small talk) — nothing to verify against.
        return True

    verdict = await llm.ainvoke(
        VERIFIER_PROMPT.format(context=context, answer=answer.content)
    )
    return "UNGROUNDED" not in str(verdict.content).upper()
