from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda

FALLBACK_MESSAGE = "I'm having trouble reaching the language model right now. Please try again shortly."

LLM_RETRY_ATTEMPTS = 3


def _fallback_response(_input: object) -> AIMessage:
    return AIMessage(content=FALLBACK_MESSAGE)


def with_resilience(llm: Runnable) -> Runnable:
    return llm.with_retry(stop_after_attempt=LLM_RETRY_ATTEMPTS).with_fallbacks(
        [RunnableLambda(_fallback_response)]
    )
