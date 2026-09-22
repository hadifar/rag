from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import Runnable

GUARDRAIL_PROMPT = (
    "You are a scope classifier for a support assistant that only answers questions about "
    "the AtlasFlow product (workflows, integrations, billing, security, API, etc.). Given "
    "the user's latest message, reply with exactly one word: RELEVANT if it's a question "
    "about AtlasFlow or its product/support domain, or IRRELEVANT if it's unrelated "
    "(small talk, general knowledge, other products, etc.).\n\nMESSAGE:\n{message}"
)

OFF_TOPIC_INSTRUCTION = (
    "The user's question is unrelated to AtlasFlow. Politely explain that you can only "
    "help with AtlasFlow questions, and ask them to rephrase around AtlasFlow's product, "
    "features, or support topics. Do not use search_kb or attempt to answer the question itself."
)


def _latest_human_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage) and message.content:
            return str(message.content)
    return ""


async def is_relevant(llm: Runnable, messages: list[BaseMessage]) -> bool:
    message = _latest_human_message(messages)
    if not message:
        return True

    verdict = await llm.ainvoke(GUARDRAIL_PROMPT.format(message=message))
    return "IRRELEVANT" not in str(verdict.content).upper()
