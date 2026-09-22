from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import Runnable

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


def _collect_context(messages: list[BaseMessage]) -> str:
    return "\n\n".join(
        str(m.content) for m in messages if isinstance(m, ToolMessage) and m.content
    )


async def is_grounded(llm: Runnable, messages: list[BaseMessage]) -> bool:
    context = _collect_context(messages)
    answer = messages[-1]

    if not context or not isinstance(answer, AIMessage) or not answer.content:
        # Nothing was retrieved this turn (e.g. small talk) — nothing to verify against.
        return True

    verdict = await llm.ainvoke(
        VERIFIER_PROMPT.format(context=context, answer=answer.content)
    )
    return "UNGROUNDED" not in str(verdict.content).upper()
