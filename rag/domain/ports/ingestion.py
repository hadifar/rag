import uuid
from typing import Protocol

from rag.domain.models import (
    Chunk,
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    RawDocument,
)


class DocumentIndexPort(Protocol):
    """The write side of the knowledge base: what's indexed, and replacing it."""

    async def alist_content_hashes(self) -> dict[str, str]:
        """source_id -> content hash, for every indexed document."""
        ...

    async def areplace_documents(
        self, documents: list[IndexedDocument], *, removed: list[str]
    ) -> None:
        """Re-indexes `documents` (embedding their chunks) and drops `removed`, all in
        one transaction.
        """
        ...


class ArchiveStorePort(Protocol):
    """Keeps every uploaded knowledge-base zip, so the index can always be rebuilt."""

    async def asave(self, data: bytes) -> str:
        """Stores `data` under a new name and returns it. Names sort by upload time."""
        ...

    async def aread(self, name: str) -> bytes: ...
    async def alatest(self) -> str | None:
        """The most recently saved archive's name, or None if there are none."""
        ...


class IngestionRunRepositoryPort(Protocol):
    async def create(
        self, archive_name: str, created_by: uuid.UUID | None
    ) -> IngestionRun:
        """Starts a run as `running`; raises IngestionInProgressError if one already is."""
        ...

    async def get(self, run_id: uuid.UUID) -> IngestionRun | None: ...
    async def latest(self) -> IngestionRun | None: ...
    async def running(self) -> IngestionRun | None: ...
    async def finish(self, run_id: uuid.UUID, report: IngestionReport) -> None: ...
    async def fail(self, run_id: uuid.UUID, error: str) -> None: ...
    async def fail_running(self, error: str) -> int:
        """Marks every still-running run failed; returns how many there were."""
        ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Chunk]: ...
