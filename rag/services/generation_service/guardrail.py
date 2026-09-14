"""Scope guardrail: flags questions unrelated to AtlasFlow before a retrieval/
generation cycle is spent on them.

Classification only decides *whether* to inject an off-topic instruction — the
actual decline text is still generated (and streamed) by the agent node itself,
so it goes through the one, already-correct streaming path instead of needing
a second one.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

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


async def is_relevant(llm: BaseChatModel, messages: list[BaseMessage]) -> bool:
    message = _latest_human_message(messages)
    if not message:
        return True

    verdict = await llm.ainvoke(GUARDRAIL_PROMPT.format(message=message))
    return "IRRELEVANT" not in str(verdict.content).upper()
