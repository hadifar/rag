import re
from itertools import takewhile

from rag.domain.models import Chunk, RawDocument

_TITLE = re.compile(r"^# +(.+?)\s*$", re.MULTILINE)
_SUBHEADING = re.compile(r"^#{2,6} +(.+?)\s*$", re.MULTILINE)


class WholeDocumentChunker:
    """Treats each document as a single chunk (no splitting).

    Chunk ids are deterministic (source_id::0), so re-running ingestion after
    a doc edit upserts over the existing vector instead of duplicating it.
    The chunk's `summary` metadata is the document's own outline (see
    `markdown_summary`); a document without one gets no `summary`.
    """

    def chunk(self, document: RawDocument) -> list[Chunk]:
        text = document.text.strip()
        if not text:
            return []
        summary = markdown_summary(text)
        return [
            Chunk(
                id=f"{document.source_id}::0",
                text=text,
                metadata={
                    **document.metadata,
                    "source_id": document.source_id,
                    "chunk_index": 0,
                    **({"summary": summary} if summary else {}),
                },
            )
        ]


def markdown_summary(text: str) -> str:
    """The `# title`, the paragraph right under it (the description), and every other
    heading as keywords:

        AtlasFlow Plans and Pricing
        This document summarizes the commercial plan structure for AtlasFlow.
        Keywords: Plan overview, Starter, Growth

    Empty when the document has none of them.
    """
    title = _TITLE.search(text)
    keywords = _SUBHEADING.findall(text)
    parts = [
        title.group(1) if title else "",
        _first_paragraph(text[title.end() :]) if title else "",
        f"Sections: {', '.join(keywords)}" if keywords else "",
    ]
    return "\n".join(part for part in parts if part)


def _first_paragraph(text: str) -> str:
    """The lines up to the first blank line or heading, joined into one line."""
    lines = takewhile(
        lambda line: line and not line.startswith("#"),
        (line.strip() for line in text.strip().splitlines()),
    )
    return " ".join(lines)
