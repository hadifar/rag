import io
import zipfile
import zlib
from collections import Counter
from pathlib import Path, PurePath, PurePosixPath

from rag.domain.errors import InvalidArchiveError
from rag.domain.models import RawDocument

# Zip-bomb guards: a small upload can declare, or inflate to, far more than it looks.
MAX_ARCHIVE_MEMBERS = 1000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


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

    Read in memory, never extracted, so member paths like `../../x` can't write
    anywhere. The basename is the source_id, as for a directory, so folders inside
    the zip don't change ids, and two files with the same basename are rejected.
    """
    try:
        zip_file = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise InvalidArchiveError("not a zip file") from exc

    with zip_file:
        members = [info for info in zip_file.infolist() if _is_markdown(info)]
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise InvalidArchiveError(f"more than {MAX_ARCHIVE_MEMBERS} markdown files")
        documents = []
        budget = MAX_UNCOMPRESSED_BYTES
        for info in members:
            data = _read_member(zip_file, info, budget)
            budget -= len(data)
            documents.append(_to_document(info, data))

    if not documents:
        raise InvalidArchiveError("no .md files found")
    _reject_duplicate_names(documents)
    return documents


def _is_markdown(info: zipfile.ZipInfo) -> bool:
    """Skips folders, and hidden/OS-metadata entries (.DS_Store, __MACOSX/)."""
    path = PurePosixPath(info.filename)
    return (
        not info.is_dir()
        and path.suffix.lower() == ".md"
        and not any(part.startswith(".") or part == "__MACOSX" for part in path.parts)
    )


def _read_member(
    zip_file: zipfile.ZipFile, info: zipfile.ZipInfo, budget: int
) -> bytes:
    """Reads at most budget + 1 bytes, so a member lying about its size in the zip
    header still can't inflate past the budget.
    """
    try:
        with zip_file.open(info) as member:
            data = member.read(budget + 1)
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError) as exc:
        # NotImplementedError: unsupported compression; RuntimeError: encrypted.
        raise InvalidArchiveError(f"can't read {info.filename}") from exc
    if len(data) > budget:
        raise InvalidArchiveError(
            f"contents exceed {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB uncompressed"
        )
    return data


def _to_document(info: zipfile.ZipInfo, data: bytes) -> RawDocument:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidArchiveError(f"{info.filename} isn't UTF-8 text") from exc
    return _raw_document(PurePosixPath(info.filename), text)


def _raw_document(path: PurePath, text: str) -> RawDocument:
    """The file name is the source_id, so a document keeps its id across folders."""
    return RawDocument(source_id=path.name, text=text, metadata={"title": path.stem})


def _reject_duplicate_names(documents: list[RawDocument]) -> None:
    counts = Counter(document.source_id for document in documents)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise InvalidArchiveError(f"duplicate file names: {', '.join(duplicates)}")
