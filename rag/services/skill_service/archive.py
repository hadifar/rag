import io
import re
import zipfile
import zlib

from rag.domain.errors import InvalidSkillError
from rag.shared import zip_reader
from rag.shared.text_normalizer import normalize_text

MAX_FILES = 50  # reference files, beside its SKILL.md
MAX_FILE_BYTES = 100 * 1024  # one reference file
MAX_TOTAL_BYTES = 500 * 1024  # every file in it, SKILL.md included, uncompressed
MAX_PATH_LENGTH = 255

SKILL_FILE = "SKILL.md"

# How a zip archive starts: its first entry, or the end of an empty one.
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06")

# An absolute path, an empty part, a Windows separator or a drive.
_UNUSABLE_PATH = re.compile(r"^/|//|[\\:]")


def is_archive(data: bytes) -> bool:
    """Whether the upload is a zip archive (a .zip or .skill file), by its content."""
    return data[:4] in _ZIP_MAGIC


def read_archive(data: bytes, max_skill_bytes: int) -> tuple[bytes, dict[str, str]]:
    """A skill archive's SKILL.md, and its other files' text by path relative to it.
    SKILL.md is at the top of the archive or in its one folder (`my-skill/SKILL.md`,
    as a .skill file holds it). Every other file must be UTF-8 text: the agent can only
    read it, never run or view it. Folders, dotfiles and `__MACOSX/` are left out.

    Sizes are checked as the archive declares them before anything is read, and again
    as it is read (see `zip_reader`). Raises `InvalidSkillError` saying what's wrong.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return _read_skill(archive, max_skill_bytes)
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, EOFError):
        raise InvalidSkillError("it isn't a readable zip archive") from None
    except zip_reader.ZipReadError as exc:
        raise InvalidSkillError(str(exc)) from exc


def _read_skill(
    archive: zipfile.ZipFile, max_skill_bytes: int
) -> tuple[bytes, dict[str, str]]:
    entries = _entries(archive)
    root = _root(entries)
    if len(entries) - 1 > MAX_FILES:
        raise InvalidSkillError(
            f"it holds more than {MAX_FILES} files beside its {SKILL_FILE}"
        )
    if sum(e.file_size for e in entries.values()) > MAX_TOTAL_BYTES:
        raise InvalidSkillError(
            f"its files add up to more than {MAX_TOTAL_BYTES // 1024} KB"
        )
    skill_entry = entries.pop(root + SKILL_FILE)
    skill = zip_reader.read_capped(archive, skill_entry, max_skill_bytes)
    files = {
        path.removeprefix(root): _text(
            path, zip_reader.read_capped(archive, entry, MAX_FILE_BYTES)
        )
        for path, entry in sorted(entries.items())
    }
    return skill, files


def _entries(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """The archive's files by path (see `zip_reader.files`)."""
    entries: dict[str, zipfile.ZipInfo] = {}
    for entry in zip_reader.files(archive):
        path = entry.filename
        _check_path(path)
        if path in entries:
            raise InvalidSkillError(f"it holds {path} twice")
        entries[path] = entry
    return entries


def _check_path(path: str) -> None:
    """A path is only ever a key the agent names a file by, never written to disk; it
    is still held to a plain relative one. (A `.` or `..` part was left out already,
    as a dotfile.)
    """
    if (
        len(path) > MAX_PATH_LENGTH
        or not path.isprintable()
        or _UNUSABLE_PATH.search(path)
    ):
        raise InvalidSkillError(f"it holds a file with an unusable path: {path!r}")


def _root(entries: dict[str, zipfile.ZipInfo]) -> str:
    """The folder SKILL.md is in: "" for the archive's top, or its one folder's name
    and a slash.
    """
    if SKILL_FILE in entries:
        return ""
    folders = {path.split("/")[0] + "/" for path in entries}
    if len(folders) == 1 and (root := folders.pop()) + SKILL_FILE in entries:
        return root
    raise InvalidSkillError(
        f"it must hold a {SKILL_FILE} at its top, or in its only folder"
    )


def _text(path: str, content: bytes) -> str:
    """The file's text, normalized as users' free text is (`normalize_text`), so
    nothing hidden in it reaches the model.
    """
    text = zip_reader.decode_text(content)
    if text is None:
        raise InvalidSkillError(
            f"{path} isn't UTF-8 text; a skill can only hold text files"
        )
    return normalize_text(text)
