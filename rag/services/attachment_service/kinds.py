from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol


class AttachmentKind(Protocol):
    """A kind of file that can be attached: recognized by its content (and, for text,
    its name), never by the type the client claims.
    """

    @property
    def media_type(self) -> str: ...
    @property
    def label(self) -> str:
        """How the user names it, e.g. ".png"."""
        ...

    @property
    def max_bytes(self) -> int: ...
    def accepts(self, name: str, data: bytes) -> bool: ...


@dataclass(frozen=True)
class SignatureKind:
    """A binary format told by the bytes it starts with."""

    media_type: str
    label: str
    max_bytes: int
    signature: bytes

    def accepts(self, name: str, data: bytes) -> bool:
        return data.startswith(self.signature)


@dataclass(frozen=True)
class TextKind:
    """A text format told by its file extension, and UTF-8 text throughout."""

    media_type: str
    label: str
    max_bytes: int
    extensions: frozenset[str]

    def accepts(self, name: str, data: bytes) -> bool:
        if PurePosixPath(name).suffix.lower() not in self.extensions or b"\0" in data:
            return False
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True


# A new kind joins here, and gets its rendering for the model in
# rag/services/agent_service/attachments.py.
KINDS: tuple[AttachmentKind, ...] = (
    TextKind(
        media_type="text/markdown",
        label=".md",
        max_bytes=200 * 1024,
        extensions=frozenset({".md", ".markdown"}),
    ),
    SignatureKind(
        media_type="image/png",
        label=".png",
        max_bytes=5 * 1024 * 1024,
        signature=b"\x89PNG\r\n\x1a\n",
    ),
    SignatureKind(
        media_type="image/jpeg",
        label=".jpg",
        max_bytes=5 * 1024 * 1024,
        signature=b"\xff\xd8\xff",
    ),
)
