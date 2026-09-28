import re
from itertools import pairwise

from langchain_core.documents import Document

from rag.domain.models import RawDocument

_HEADING_RE = re.compile(r"^(#{1,3})\s+.*$", re.MULTILINE)


class MarkdownHeaderChunker:
    """Splits on markdown headings (#, ##, ###); one chunk per section.

    Chunk ids are deterministic (source_id::index), so re-running ingestion after
    a doc edit upserts over the existing vectors instead of duplicating them.
    """

    def chunk(self, document: RawDocument) -> list[Document]:
        matches = list(_HEADING_RE.finditer(document.text))
        if not matches:
            sections = [(0, document.text.strip())]
        else:
            bounds = [m.start() for m in matches] + [len(document.text)]
            sections = [
                (index, document.text[start:end].strip())
                for index, (start, end) in enumerate(pairwise(bounds))
            ]

        return [_chunk(document, index, text) for index, text in sections if text]


class WholeDocumentChunker:
    """Treats each document as a single chunk (no splitting).

    Chunk ids are deterministic (source_id::0), so re-running ingestion after
    a doc edit upserts over the existing vector instead of duplicating it.
    """

    def chunk(self, document: RawDocument) -> list[Document]:
        text = document.text.strip()
        return [_chunk(document, 0, text)] if text else []


def _chunk(document: RawDocument, index: int, text: str) -> Document:
    return Document(
        id=f"{document.source_id}::{index}",
        page_content=text,
        metadata={
            **document.metadata,
            "source_id": document.source_id,
            "chunk_index": index,
        },
    )
