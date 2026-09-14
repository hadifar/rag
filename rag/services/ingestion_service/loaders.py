from collections.abc import Iterator
from pathlib import Path

from rag.domain.models import RawDocument


class MarkdownFileLoader:
    """Concrete DocumentLoaderPort for the local markdown knowledge base.

    Adding a new source (PDFs, Confluence, ...) means writing another class with
    the same load() -> Iterable[RawDocument] shape — IngestionService, chunking,
    and the vector store adapter stay untouched.
    """

    def __init__(self, directory: Path):
        self._directory = directory

    def load(self) -> Iterator[RawDocument]:
        for path in sorted(self._directory.glob("*.md")):
            yield RawDocument(
                source_id=path.name,
                text=path.read_text(),
                metadata={"title": path.stem},
            )
