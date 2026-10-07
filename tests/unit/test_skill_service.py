import io
import uuid
import zipfile

import pytest

from rag.domain.errors import (
    InvalidSkillError,
    SkillNotFoundError,
    SkillTooLargeError,
    TooManySkillsError,
)
from rag.domain.models import SkillContent
from rag.services.skill_service.service import MAX_SKILLS, SkillService
from tests.unit.fakes import FakeSkillRepository

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _skill_file(
    name: str = "release-notes",
    description: str = "Write release notes from a list of changes.",
    body: str = "# Release notes\n\nGroup the changes by area.",
) -> bytes:
    return f"---\nname: {name}\ndescription: {description}\n---\n{body}\n".encode()


def _archive(files: dict[str, bytes | str]) -> bytes:
    """A zip archive of `files`, by path."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def _service() -> SkillService:
    return SkillService(skills=FakeSkillRepository())


def _saved() -> tuple[SkillService, FakeSkillRepository]:
    """The service, and the repository it saves to, to read back what it saved."""
    skills = FakeSkillRepository()
    return SkillService(skills=skills), skills


async def _instructions(skills: FakeSkillRepository, user: uuid.UUID, name: str) -> str:
    content = await skills.content(user, name)
    assert content is not None
    return content.instructions


async def test_an_upload_is_saved_as_a_skill_with_its_instructions() -> None:
    service, skills = _saved()

    skill = await service.upload(ALICE, _skill_file())

    assert skill.name == "release-notes"
    assert skill.description == "Write release notes from a list of changes."
    assert await service.list_for_user(ALICE) == [skill]
    assert await skills.content(ALICE, "release-notes") == SkillContent(
        "# Release notes\n\nGroup the changes by area.", files=()
    )
    assert skill.file_count == 0


async def test_frontmatter_is_read_as_yaml() -> None:
    service, skills = _saved()
    data = (
        "﻿---\r\n"
        'name: "tone-guide"\r\n'
        "description: >\r\n"
        "  Answer formally,\r\n"
        "  in short paragraphs.\r\n"
        "license: MIT\r\n"
        "---\r\n"
        "Be formal.\r\n"
    ).encode()

    skill = await service.upload(ALICE, data)

    assert skill.name == "tone-guide"
    assert skill.description == "Answer formally, in short paragraphs."
    assert await _instructions(skills, ALICE, "tone-guide") == "Be formal."


async def test_uploading_a_skill_of_the_same_name_replaces_it() -> None:
    service, skills = _saved()
    first = await service.upload(ALICE, _skill_file(body="old"))

    second = await service.upload(ALICE, _skill_file(body="new"))

    assert second.id == first.id
    assert await service.list_for_user(ALICE) == [second]
    assert await _instructions(skills, ALICE, "release-notes") == "new"


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"# Just markdown", "frontmatter"),
        (b"---\nname: [unclosed\n---\nbody", "valid YAML"),
        (b"---\n- a list\n---\nbody", "key: value"),
        (_skill_file(name=""), "no `name`"),
        (_skill_file(name="Release Notes"), "lowercase"),
        (_skill_file(name="a" * 65), "lowercase"),
        (_skill_file(description=""), "no `description`"),
        (_skill_file(description="x" * 1025), "1024"),
        (_skill_file(body="   "), "no instructions"),
        (b"\xff\xfe---", "UTF-8"),
    ],
)
async def test_an_invalid_skill_file_is_rejected_saying_why(
    data: bytes, reason: str
) -> None:
    with pytest.raises(InvalidSkillError, match=reason):
        await _service().upload(ALICE, data)


async def test_a_skill_file_over_the_limit_is_rejected() -> None:
    with pytest.raises(SkillTooLargeError, match="50 KB"):
        await _service().upload(ALICE, _skill_file(body="x" * 50 * 1024))


async def test_a_user_can_save_only_so_many_skills_but_still_replace_one() -> None:
    service = _service()
    for i in range(MAX_SKILLS):
        await service.upload(ALICE, _skill_file(name=f"skill-{i}"))

    with pytest.raises(TooManySkillsError):
        await service.upload(ALICE, _skill_file(name="one-more"))
    await service.upload(ALICE, _skill_file(name="skill-0", body="replaced"))
    await service.upload(BOB, _skill_file(name="one-more"))  # the limit is per user


async def test_a_users_skills_are_theirs_alone() -> None:
    service, skills = _saved()
    skill = await service.upload(ALICE, _skill_file())

    assert await service.list_for_user(BOB) == []
    assert await skills.content(BOB, "release-notes") is None
    with pytest.raises(SkillNotFoundError):
        await service.delete(BOB, skill.id)

    await service.delete(ALICE, skill.id)
    assert await service.list_for_user(ALICE) == []


@pytest.mark.parametrize(
    "files",
    [
        # SKILL.md at the archive's top, or in its one folder (a .skill file's layout).
        {"SKILL.md": _skill_file(), "references/api.md": "# API", "a.py": "x = 1"},
        {
            "release-notes/SKILL.md": _skill_file(),
            "release-notes/references/api.md": "# API",
            "release-notes/a.py": "x = 1",
        },
    ],
)
async def test_an_archive_is_saved_with_its_reference_files(
    files: dict[str, bytes | str],
) -> None:
    service, skills = _saved()

    skill = await service.upload(ALICE, _archive(files))

    assert skill.name == "release-notes"
    assert skill.file_count == 2
    assert await skills.content(ALICE, "release-notes") == SkillContent(
        "# Release notes\n\nGroup the changes by area.",
        files=("a.py", "references/api.md"),
    )
    assert await skills.file(ALICE, "release-notes", "references/api.md") == "# API"
    assert await skills.file(BOB, "release-notes", "references/api.md") is None


async def test_an_archive_leaves_out_folders_dotfiles_and_mac_metadata() -> None:
    service, skills = _saved()
    data = _archive(
        {
            "SKILL.md": _skill_file(),
            "notes/": "",
            ".DS_Store": b"\x00\x01",
            "notes/.hidden.md": "hidden",
            "__MACOSX/._SKILL.md": b"\x00\x01",
            "../escape.md": "outside",
            "notes/keep.md": "kept",
        }
    )

    skill = await service.upload(ALICE, data)

    assert skill.file_count == 1
    assert await skills.file(ALICE, "release-notes", "notes/keep.md") == "kept"


async def test_uploading_a_skill_again_replaces_its_files() -> None:
    service, skills = _saved()
    await service.upload(ALICE, _archive({"SKILL.md": _skill_file(), "old.md": "o"}))

    skill = await service.upload(ALICE, _skill_file())

    assert skill.file_count == 0
    assert await skills.file(ALICE, "release-notes", "old.md") is None


async def test_a_reference_file_is_normalized_as_free_text_is() -> None:
    service, skills = _saved()
    hidden = "Be\u200b brief.\U000e0041"
    await service.upload(ALICE, _archive({"SKILL.md": _skill_file(), "s.md": hidden}))

    assert await skills.file(ALICE, "release-notes", "s.md") == "Be brief."


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        ({"README.md": "no skill"}, "must hold a SKILL.md"),
        ({"a/SKILL.md": _skill_file(), "b/x.md": "x"}, "must hold a SKILL.md"),
        ({"a/b/SKILL.md": _skill_file()}, "must hold a SKILL.md"),
        ({"SKILL.md": "# no frontmatter"}, "frontmatter"),
        ({"SKILL.md": _skill_file(), "logo.png": b"\x89PNG\x00"}, "logo.png isn't"),
        ({"SKILL.md": _skill_file(), "bad.md": b"\xff\xfe"}, "bad.md isn't"),
        ({"SKILL.md": _skill_file(), "/abs.md": "x"}, "unusable path"),
        ({"SKILL.md": _skill_file(), "a//b.md": "x"}, "unusable path"),
        ({"SKILL.md": _skill_file(), "a\\b.md": "x"}, "unusable path"),
        ({"SKILL.md": _skill_file(), "C:x.md": "x"}, "unusable path"),
        ({"SKILL.md": _skill_file(), "big.md": "x" * (100 * 1024 + 1)}, "100 KB"),
        ({"SKILL.md": _skill_file(body="x" * 50 * 1024)}, "SKILL.md is larger"),
        (
            {"SKILL.md": _skill_file(), **{f"{i}.md": "x" for i in range(51)}},
            "more than 50 files",
        ),
        (
            {"SKILL.md": _skill_file(), **{f"{i}.md": "x" * 90_000 for i in range(6)}},
            "more than 500 KB",
        ),
    ],
)
async def test_an_invalid_archive_is_rejected_saying_why(
    files: dict[str, bytes | str], reason: str
) -> None:
    with pytest.raises(InvalidSkillError, match=reason):
        await _service().upload(ALICE, _archive(files))


async def test_an_archive_that_is_not_a_readable_zip_is_rejected() -> None:
    with pytest.raises(InvalidSkillError, match="readable zip"):
        await _service().upload(ALICE, b"PK\x03\x04 truncated")


async def test_an_archive_over_the_upload_limit_is_rejected() -> None:
    stored = io.BytesIO()
    with zipfile.ZipFile(stored, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("SKILL.md", _skill_file())
        archive.writestr("noise.bin", bytes(range(256)) * 2100)

    with pytest.raises(SkillTooLargeError, match="512 KB"):
        await _service().upload(ALICE, stored.getvalue())


async def test_an_archive_that_lies_about_its_sizes_is_read_no_further() -> None:
    data = bytearray(_archive({"SKILL.md": _skill_file(), "bomb.md": "x" * 200_000}))
    # Rewrite the declared uncompressed size of bomb.md (in its local header and the
    # central directory) to 10 bytes: it's read no further than that, and fails its
    # checksum.
    size = (200_000).to_bytes(4, "little")
    assert data.count(size) == 2
    data = bytearray(bytes(data).replace(size, (10).to_bytes(4, "little")))

    with pytest.raises(InvalidSkillError, match="can't read bomb.md"):
        await _service().upload(ALICE, bytes(data))
