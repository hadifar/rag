RERANK_PROMPT = (
    "Judge whether each passage below is relevant to the user's question: relevant "
    "if it could help answer the question, even only part of it. Each passage is "
    "shown by its summary; give a verdict on every passage by its index.\n\n"
    "QUESTION:\n{query}\n\n"
    "PASSAGES:\n{passages}"
)
