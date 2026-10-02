from dataclasses import dataclass

MAX_PREFERENCES = 20  # per user; every one is added to each of their chat turns' prompt
MAX_PREFERENCE_LENGTH = 200


@dataclass(frozen=True)
class Preference:
    """Something the user wants of every answer (e.g. "Answer in Dutch"), in their own
    words. Kept per user, across all their conversations.
    """

    id: str
    text: str
