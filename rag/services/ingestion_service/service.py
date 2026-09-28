import asyncio
import hashlib

from rag.domain.errors import EmptyKnowledgeBaseError, NoArchiveError
from rag.domain.models import IndexedDocument, IngestionReport, RawDocument
from rag.domain.ports import (
    ArchiveStorePort,
    ChunkerPort,
    DocumentIndexPort,
    DocumentLoaderPort,
)
from rag.services.ingestion_service.loaders import ZipMarkdownLoader


class IngestionService:
    """Makes the index match a source.

    Only new or changed documents (by content hash) are chunked and embedded, and
    documents the source no longer has are removed — all in one transaction, so a
    failed run leaves the previous index intact.
    """

    def __init__(
        self,
        index: DocumentIndexPort,
        chunker: ChunkerPort,
        archives: ArchiveStorePort,
    ):
        self._index = index
        self._chunker = chunker
        self._archives = archives

    async def save_archive(self, archive: bytes) -> str:
        """Validates the zip, then keeps it; returns its name. An invalid zip raises
        InvalidArchiveError and is never stored.
        """
        await asyncio.to_thread(ZipMarkdownLoader, archive)
        return await self._archives.asave(archive)

    async def ingest_archive(
        self, name: str, *, force: bool = False
    ) -> IngestionReport:
        archive = await self._archives.aread(name)
        loader = await asyncio.to_thread(ZipMarkdownLoader, archive)
        return await self.ingest(loader, force=force)

    async def ingest_latest_archive(self, *, force: bool = False) -> IngestionReport:
        """Rebuilds the index from the most recent upload (e.g. after losing the DB)."""
        name = await self._archives.alatest()
        if name is None:
            raise NoArchiveError()
        return await self.ingest_archive(name, force=force)

    async def ingest(
        self,
        loader: DocumentLoaderPort,
        *,
        force: bool = False,
        remove_missing: bool = True,
    ) -> IngestionReport:
        """`force` re-embeds unchanged documents too (e.g. after changing the
        embedding model or chunker); `remove_missing=False` only adds and updates.
        """
        documents = list(loader.load())
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
