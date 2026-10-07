"""Reading an uploaded zip in memory, never extracting it, so its paths can't write
anywhere; and capped, so a small upload that inflates to far more is never held whole.
"""

import zipfile
import zlib
from pathlib import PurePosixPath


class ZipReadError(ValueError):
    """Why the archive can't be read, fit to show the user."""


def files(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """The archive's files: no folders, dotfiles, or macOS's `__MACOSX/` metadata."""
    return [
        entry
        for entry in archive.infolist()
        if not entry.is_dir()
        and not any(
            part == "__MACOSX" or part.startswith(".")
            for part in PurePosixPath(entry.filename).parts
        )
    ]


def read_capped(archive: zipfile.ZipFile, entry: zipfile.ZipInfo, limit: int) -> bytes:
    """The file's content; raises `ZipReadError` if it's encrypted, can't be read, or
    holds more than `limit` bytes, as the archive declares it or as it inflates.
    """
    if entry.flag_bits & 0x1:
        raise ZipReadError(f"{entry.filename} is encrypted")
    if entry.file_size > limit:
        raise ZipReadError(f"{entry.filename} is larger than {_size(limit)}")
    try:
        with archive.open(entry) as file:
            # One byte past the limit is enough to tell a size the archive lied about.
            content = file.read(limit + 1)
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, EOFError):
        # NotImplementedError: a compression method zipfile doesn't support.
        raise ZipReadError(f"can't read {entry.filename}") from None
    if len(content) > limit:
        raise ZipReadError(f"{entry.filename} is larger than {_size(limit)}")
    return content


def decode_text(content: bytes) -> str | None:
    """The content as UTF-8 text (a BOM dropped); None if it isn't text, NULs included:
    they decode, but no text file holds one.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    return None if "\x00" in text else text


def _size(limit: int) -> str:
    mb = 1024 * 1024
    return f"{limit // mb} MB" if limit >= mb else f"{limit // 1024} KB"
