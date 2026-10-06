from typing import Annotated

from pydantic import BeforeValidator

from rag.shared.text_normalizer import normalize_text


def _normalized(value: object) -> object:
    # Anything but a string is left for the str check to reject.
    return normalize_text(value) if isinstance(value, str) else value


# Text a user typed, normalized before the field's own checks run, so its length and
# emptiness are those of the text that is kept.
UserText = Annotated[str, BeforeValidator(_normalized)]
