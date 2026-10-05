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
    "features, or support topics. Do not attempt to answer the question itself."
)

FALLBACK_MESSAGE = "I'm having trouble reaching the language model right now. Please try again shortly."

# Shown to the user when a turn fails (see TurnFailed).
TURN_FAILED_MESSAGE = "Something went wrong while answering. Please try again."
