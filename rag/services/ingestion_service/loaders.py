import io
import zipfile
from collections import Counter
from pathlib import Path, PurePath, PurePosixPath

from rag.domain.errors import InvalidArchiveError
from rag.domain.models import RawDocument
from rag.shared import zip_reader

# Zip-bomb guards: a small upload can declare, or inflate to, far more than it looks.
MAX_ARCHIVE_MEMBERS = 1000  # markdown files in one archive
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # what the archive may expand to


def load_path(path: Path) -> list[RawDocument]:
    """A directory of .md files, or a .zip of them."""
    return load_directory(path) if path.is_dir() else load_archive(path.read_bytes())


def load_directory(directory: Path) -> list[RawDocument]:
    """Every .md file directly in `directory`."""
    return [
        _raw_document(path, path.read_text()) for path in sorted(directory.glob("*.md"))
    ]


def load_archive(archive: bytes) -> list[RawDocument]:
    """Every .md file in a zip, at any depth. Raises InvalidArchiveError for a bad one.

    Read in memory, never extracted (see `zip_reader`). The basename is the source_id,
    as for a directory, so folders inside the zip don't change ids, and two files with
    the same basename are rejected.
    """
    try:
        zip_file = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise InvalidArchiveError("not a zip file") from exc

    with zip_file:
        try:
            documents = _read_documents(zip_file, _markdown_members(zip_file))
        except zip_reader.ZipReadError as exc:
            raise InvalidArchiveError(str(exc)) from exc

    if not documents:
        raise InvalidArchiveError("no .md files found")
    _reject_duplicate_names(documents)
    return documents


def _markdown_members(zip_file: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """The .md files, checked against the caps as the archive declares them."""
    members = [
        info
        for info in zip_reader.files(zip_file)
        if PurePosixPath(info.filename).suffix.lower() == ".md"
    ]
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise InvalidArchiveError(f"more than {MAX_ARCHIVE_MEMBERS} markdown files")
    if sum(info.file_size for info in members) > MAX_UNCOMPRESSED_BYTES:
        raise InvalidArchiveError(
            f"contents exceed {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB uncompressed"
        )
    return members


def _read_documents(
    zip_file: zipfile.ZipFile, members: list[zipfile.ZipInfo]
) -> list[RawDocument]:
    """Read within what is left of the cap, so a member that lies about its size still
    can't inflate past it.
    """
    documents: list[RawDocument] = []
    budget = MAX_UNCOMPRESSED_BYTES
    for info in members:
        data = zip_reader.read_capped(zip_file, info, budget)
        budget -= len(data)
        documents.append(_to_document(info, data))
    return documents


def _to_document(info: zipfile.ZipInfo, data: bytes) -> RawDocument:
    text = zip_reader.decode_text(data)
    if text is None:
        raise InvalidArchiveError(f"{info.filename} isn't UTF-8 text")
    return _raw_document(PurePosixPath(info.filename), text)


def _raw_document(path: PurePath, text: str) -> RawDocument:
    """The file name is the source_id, so a document keeps its id across folders."""
    return RawDocument(source_id=path.name, text=text, metadata={"title": path.stem})


def _reject_duplicate_names(documents: list[RawDocument]) -> None:
    counts = Counter(document.source_id for document in documents)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise InvalidArchiveError(f"duplicate file names: {', '.join(duplicates)}")
