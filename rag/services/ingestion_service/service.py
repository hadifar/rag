import asyncio
import hashlib
import logging
import uuid

from rag.domain.errors import (
    ArchiveTooLargeError,
    EmptyKnowledgeBaseError,
    IngestionInProgressError,
    IngestionRunNotFoundError,
    NoArchiveError,
    RagError,
)
from rag.domain.models import (
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    RawDocument,
)
from rag.domain.ports import (
    ArchiveStorePort,
    ChunkerPort,
    DocumentIndexPort,
    IngestionRunRepositoryPort,
)
from rag.services.ingestion_service.loaders import load_archive

logger = logging.getLogger(__name__)

# Keep in sync with client_max_body_size for /api/ingestions in nginx.conf.template.
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024


class IngestionService:
    """Makes the index match a source.

    Only new or changed documents (by content hash) are chunked and embedded, and
    documents the source no longer has are removed — all in one transaction, so a
    failed run leaves the previous index intact.

    Uploads go through runs: `start_upload` validates and stores the zip and records a
    `running` run (at most one at a time); `complete_run` then does the ingestion,
    meant to run in the background, and records how it ended.
    """

    def __init__(
        self,
        index: DocumentIndexPort,
        chunker: ChunkerPort,
        archives: ArchiveStorePort,
        runs: IngestionRunRepositoryPort,
    ):
        self._index = index
        self._chunker = chunker
        self._archives = archives
        self._runs = runs

    @property
    def max_archive_bytes(self) -> int:
        """Uploads larger than this are rejected (413)."""
        return MAX_ARCHIVE_BYTES

    async def start_upload(
        self, archive: bytes, user_id: uuid.UUID | None
    ) -> IngestionRun:
        if len(archive) > MAX_ARCHIVE_BYTES:
            raise ArchiveTooLargeError(MAX_ARCHIVE_BYTES)
        # Checked before storing, so a rejected upload isn't kept. The unique index
        # behind `create` still catches two uploads racing past this check.
        if await self._runs.running() is not None:
            raise IngestionInProgressError()
        name = await self.save_archive(archive)
        return await self._runs.create(name, user_id)

    async def complete_run(self, run: IngestionRun) -> None:
        """Never raises: however the ingestion ends is recorded on the run."""
        try:
            report = await self.ingest_archive(run.archive_name)
        except RagError as exc:
            await self._runs.fail(run.id, str(exc))
        except Exception:
            logger.exception("Ingestion run %s failed", run.id)
            await self._runs.fail(
                run.id, "Ingestion failed unexpectedly; see the server logs"
            )
        else:
            await self._runs.finish(run.id, report)

    async def get_run(self, run_id: uuid.UUID) -> IngestionRun:
        run = await self._runs.get(run_id)
        if run is None:
            raise IngestionRunNotFoundError(run_id)
        return run

    async def latest_run(self) -> IngestionRun | None:
        return await self._runs.latest()

    async def fail_interrupted_runs(self) -> int:
        """At startup: a run still `running` was cut off by a restart (its background
        task died with the old process), so mark it failed instead of blocking uploads.
        """
        return await self._runs.fail_running(
            "Interrupted by a server restart; upload the archive again"
        )

    async def save_archive(self, archive: bytes) -> str:
        """Validates the zip, then keeps it; returns its name. An invalid zip raises
        InvalidArchiveError and is never stored.
        """
        await asyncio.to_thread(load_archive, archive)
        return await self._archives.asave(archive)

    async def ingest_archive(
        self, name: str, *, force: bool = False
    ) -> IngestionReport:
        archive = await self._archives.aread(name)
        documents = await asyncio.to_thread(load_archive, archive)
        return await self.ingest(documents, force=force)

    async def ingest_latest_archive(self, *, force: bool = False) -> IngestionReport:
        """Rebuilds the index from the most recent upload (e.g. after losing the DB)."""
        name = await self._archives.alatest()
        if name is None:
            raise NoArchiveError()
        return await self.ingest_archive(name, force=force)

    async def ingest(
        self,
        documents: list[RawDocument],
        *,
        force: bool = False,
        remove_missing: bool = True,
    ) -> IngestionReport:
        """`force` re-embeds unchanged documents too (e.g. after changing the
        embedding model or chunker); `remove_missing=False` only adds and updates.
        """
        if not documents:
            raise EmptyKnowledgeBaseError()

        stored = await self._index.alist_content_hashes()
        changed = [
            IndexedDocument(
                document.source_id, content_hash, self._chunker.chunk(document)
            )
            for document, content_hash in _with_hashes(documents)
            if force or stored.get(document.source_id) != content_hash
        ]
        removed = (
            sorted(stored.keys() - {document.source_id for document in documents})
            if remove_missing
            else []
        )

        await self._index.areplace_documents(changed, removed=removed)

        added = sum(1 for document in changed if document.source_id not in stored)
        return IngestionReport(
            added=added,
            updated=len(changed) - added,
            unchanged=len(documents) - len(changed),
            removed=len(removed),
            chunks=sum(len(document.chunks) for document in changed),
        )


def _with_hashes(documents: list[RawDocument]) -> list[tuple[RawDocument, str]]:
    return [
        (document, hashlib.sha256(document.text.encode()).hexdigest())
        for document in documents
    ]
