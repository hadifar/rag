from dataclasses import dataclass


@dataclass(frozen=True)
class Upload:
    """A file as the user uploaded it, not yet checked."""

    name: str  # as the client sent it, directories and all; "" if it sent none
    data: bytes
