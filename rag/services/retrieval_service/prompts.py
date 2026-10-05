RERANK_PROMPT = (
    "Rate how relevant each passage below is to the user's question, from 1 (not "
    "relevant) to 10 (answers it directly). Each passage is shown by its summary; "
    "score every passage by its index.\n\n"
    "QUESTION:\n{query}\n\n"
    "PASSAGES:\n{passages}"
)
