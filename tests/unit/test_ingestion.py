import io
import uuid
import zipfile
from pathlib import Path

import pytest

from rag.adapters.archive_store import LocalArchiveStore
from rag.domain.errors import (
    ArchiveTooLargeError,
    EmptyKnowledgeBaseError,
    IngestionInProgressError,
    IngestionRunNotFoundError,
    InvalidArchiveError,
    NoArchiveError,
)
from rag.domain.models import IngestionReport, RawDocument
from rag.services.ingestion_service import loaders, service
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.loaders import (
    MarkdownFileLoader,
    ZipMarkdownLoader,
    loader_for_path,
)
from rag.services.ingestion_service.service import IngestionService
from tests.unit.fakes import (
    FakeArchiveStore,
    FakeDocumentIndex,
    FakeIngestionRunRepository,
)


def _zip(files: dict[str, str | bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class ListLoader:
    def __init__(self, documents: dict[str, str]):
        self._documents = [
            RawDocument(source_id=k, text=v) for k, v in documents.items()
        ]

    def load(self) -> list[RawDocument]:
        return self._documents


def _service(
    index: FakeDocumentIndex,
    archives: FakeArchiveStore | None = None,
    runs: FakeIngestionRunRepository | None = None,
) -> IngestionService:
    return IngestionService(
        index,
        WholeDocumentChunker(),
        archives or FakeArchiveStore(),
        runs or FakeIngestionRunRepository(),
    )


# --- ZipMarkdownLoader -------------------------------------------------------------


def test_zip_loader_reads_markdown_at_any_depth_keyed_by_basename() -> None:
    archive = _zip({"top.md": "# Top", "kb/nested/deep.md": "# Deep"})

    documents = {d.source_id: d for d in ZipMarkdownLoader(archive).load()}

    assert documents.keys() == {"top.md", "deep.md"}
    assert documents["deep.md"].text == "# Deep"
    assert documents["deep.md"].metadata == {"title": "deep"}


def test_zip_loader_skips_non_markdown_hidden_and_macos_metadata() -> None:
    archive = _zip(
        {
            "kb/a.md": "# A",
            "kb/notes.txt": "not markdown",
            "kb/.hidden.md": "hidden",
            "__MACOSX/kb/._a.md": "resource fork",
            ".git/README.md": "vcs",
        }
    )

    assert [d.source_id for d in ZipMarkdownLoader(archive).load()] == ["a.md"]


def test_zip_loader_strips_a_utf8_bom() -> None:
    archive = _zip({"a.md": "﻿# A".encode()})

    assert next(iter(ZipMarkdownLoader(archive).load())).text == "# A"


@pytest.mark.parametrize(
    ("archive", "reason"),
    [
        (b"not a zip", "not a zip file"),
        (_zip({"readme.txt": "no markdown"}), "no .md files"),
        (_zip({"a/x.md": "1", "b/x.md": "2"}), "duplicate file names: x.md"),
        (_zip({"a.md": b"\xff\xfe\xfa"}), "isn't UTF-8"),
    ],
)
def test_zip_loader_rejects_bad_archives(archive: bytes, reason: str) -> None:
    with pytest.raises(InvalidArchiveError, match=reason):
        ZipMarkdownLoader(archive)


def test_zip_loader_caps_the_uncompressed_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loaders, "MAX_UNCOMPRESSED_BYTES", 10)
    archive = _zip({"a.md": "12345", "b.md": "678901"})

    with pytest.raises(InvalidArchiveError, match="uncompressed"):
        ZipMarkdownLoader(archive)


def test_zip_loader_caps_the_member_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loaders, "MAX_ARCHIVE_MEMBERS", 1)
    archive = _zip({"a.md": "a", "b.md": "b"})

    with pytest.raises(InvalidArchiveError, match="more than 1"):
        ZipMarkdownLoader(archive)


def test_loader_for_path_picks_directory_or_zip(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A")
    zip_path = tmp_path / "kb.zip"
    zip_path.write_bytes(_zip({"b.md": "# B"}))

    assert isinstance(loader_for_path(tmp_path), MarkdownFileLoader)
    assert isinstance(loader_for_path(zip_path), ZipMarkdownLoader)


# --- IngestionService ---------------------------------------------------------------


async def test_first_ingest_adds_everything() -> None:
    index = FakeDocumentIndex()
    service = _service(index)

    report = await service.ingest(ListLoader({"a.md": "A", "b.md": "B"}))

    assert report == IngestionReport(
        added=2, updated=0, unchanged=0, removed=0, chunks=2
    )
    assert index.hashes.keys() == {"a.md", "b.md"}


async def test_reingest_embeds_only_changed_and_removes_missing() -> None:
    index = FakeDocumentIndex()
    service = _service(index)
    await service.ingest(ListLoader({"same.md": "S", "edit.md": "v1", "gone.md": "G"}))

    report = await service.ingest(
        ListLoader({"same.md": "S", "edit.md": "v2", "new.md": "N"})
    )

    assert report == IngestionReport(
        added=1, updated=1, unchanged=1, removed=1, chunks=2
    )
    documents, removed = index.replaced[-1]
    assert sorted(d.source_id for d in documents) == ["edit.md", "new.md"]
    assert removed == ["gone.md"]
    assert index.hashes.keys() == {"same.md", "edit.md", "new.md"}


async def test_force_reembeds_unchanged_documents() -> None:
    index = FakeDocumentIndex()
    service = _service(index)
    await service.ingest(ListLoader({"a.md": "A"}))

    report = await service.ingest(ListLoader({"a.md": "A"}), force=True)

    assert (report.updated, report.unchanged, report.chunks) == (1, 0, 1)


async def test_remove_missing_false_keeps_other_documents() -> None:
    index = FakeDocumentIndex({"other.md": "hash"})
    service = _service(index)

    report = await service.ingest(ListLoader({"a.md": "A"}), remove_missing=False)

    assert report.removed == 0
    assert index.hashes.keys() == {"other.md", "a.md"}


async def test_an_empty_source_is_refused_instead_of_emptying_the_index() -> None:
    index = FakeDocumentIndex({"a.md": "hash"})
    service = _service(index)

    with pytest.raises(EmptyKnowledgeBaseError):
        await service.ingest(ListLoader({}))
    assert index.replaced == []


# --- Archives ------------------------------------------------------------------------


async def test_save_archive_keeps_a_valid_zip() -> None:
    archives = FakeArchiveStore()
    archive = _zip({"a.md": "# A"})

    name = await _service(FakeDocumentIndex(), archives).save_archive(archive)

    assert archives.archives == {name: archive}


async def test_save_archive_never_stores_an_invalid_zip() -> None:
    archives = FakeArchiveStore()

    with pytest.raises(InvalidArchiveError):
        await _service(FakeDocumentIndex(), archives).save_archive(b"not a zip")
    assert archives.archives == {}


async def test_ingest_latest_archive_uses_the_newest_upload() -> None:
    index = FakeDocumentIndex()
    service = _service(index)
    await service.save_archive(_zip({"old.md": "old"}))
    await service.save_archive(_zip({"new.md": "new"}))

    await service.ingest_latest_archive()

    assert index.hashes.keys() == {"new.md"}


async def test_ingest_latest_archive_without_uploads_raises() -> None:
    with pytest.raises(NoArchiveError):
        await _service(FakeDocumentIndex()).ingest_latest_archive()


async def test_local_archive_store_round_trips_and_finds_the_latest(
    tmp_path: Path,
) -> None:
    store = LocalArchiveStore(tmp_path / "uploads")
    assert await store.alatest() is None

    first = await store.asave(b"first")
    second = await store.asave(b"second")

    assert first < second
    assert await store.alatest() == second
    assert await store.aread(first) == b"first"
    assert sorted(p.name for p in (tmp_path / "uploads").iterdir()) == [first, second]


# --- Runs ----------------------------------------------------------------------------


async def test_upload_run_stores_the_archive_then_records_the_report() -> None:
    index, archives, runs = (
        FakeDocumentIndex(),
        FakeArchiveStore(),
        FakeIngestionRunRepository(),
    )
    ingestion = _service(index, archives, runs)

    run = await ingestion.start_upload(_zip({"a.md": "A", "b.md": "B"}), user_id=None)
    assert run.status == "running"
    assert archives.archives.keys() == {run.archive_name}

    await ingestion.complete_run(run)

    done = await ingestion.get_run(run.id)
    assert (done.status, done.added, done.chunks, done.error) == (
        "succeeded",
        2,
        2,
        None,
    )
    assert index.hashes.keys() == {"a.md", "b.md"}


async def test_upload_while_a_run_is_going_is_refused_and_not_stored() -> None:
    archives = FakeArchiveStore()
    ingestion = _service(FakeDocumentIndex(), archives)
    await ingestion.start_upload(_zip({"a.md": "A"}), user_id=None)

    with pytest.raises(IngestionInProgressError):
        await ingestion.start_upload(_zip({"b.md": "B"}), user_id=None)
    assert len(archives.archives) == 1


async def test_upload_over_the_size_limit_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "MAX_ARCHIVE_BYTES", 10)

    with pytest.raises(ArchiveTooLargeError):
        await _service(FakeDocumentIndex()).start_upload(b"x" * 11, user_id=None)


async def test_invalid_upload_starts_no_run() -> None:
    runs = FakeIngestionRunRepository()

    with pytest.raises(InvalidArchiveError):
        await _service(FakeDocumentIndex(), runs=runs).start_upload(b"nope", None)
    assert runs.runs == {}


async def test_a_failing_run_records_the_error_and_frees_the_slot() -> None:
    class BrokenIndex(FakeDocumentIndex):
        async def areplace_documents(self, documents, *, removed) -> None:
            raise ConnectionError("embedding API down")

    ingestion = _service(BrokenIndex())
    run = await ingestion.start_upload(_zip({"a.md": "A"}), user_id=None)

    await ingestion.complete_run(run)  # doesn't raise

    failed = await ingestion.get_run(run.id)
    assert failed.status == "failed"
    assert failed.error is not None and "unexpectedly" in failed.error
    await ingestion.start_upload(_zip({"a.md": "A"}), user_id=None)  # slot is free


async def test_interrupted_runs_are_failed_at_startup() -> None:
    ingestion = _service(FakeDocumentIndex())
    run = await ingestion.start_upload(_zip({"a.md": "A"}), user_id=None)

    assert await ingestion.fail_interrupted_runs() == 1
    assert (await ingestion.get_run(run.id)).status == "failed"
    assert await ingestion.latest_run() is not None


async def test_unknown_run_raises() -> None:
    with pytest.raises(IngestionRunNotFoundError):
        await _service(FakeDocumentIndex()).get_run(uuid.uuid4())
