# The custom events the guards dispatch and the stream turns into user-facing events
# (see streaming.parse_event).

# Dispatched by the guard that checks each answer: the check starting, then its verdict.
ANSWER_VERIFICATION = "answer_verification"

# Dispatched by the guard that blocks a user message, with the refusal sent instead of
# an answer.
INPUT_BLOCKED = "input_blocked"
