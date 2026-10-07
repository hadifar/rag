import uuid

import pytest

from rag.domain.errors import (
    InvalidSkillError,
    SkillNotFoundError,
    SkillTooLargeError,
    TooManySkillsError,
)
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


def _service() -> SkillService:
    return SkillService(skills=FakeSkillRepository())


async def test_an_upload_is_saved_as_a_skill_with_its_instructions() -> None:
    service = _service()

    skill = await service.upload(ALICE, _skill_file())

    assert skill.name == "release-notes"
    assert skill.description == "Write release notes from a list of changes."
    assert await service.list_for_user(ALICE) == [skill]
    assert (
        await service.instructions(ALICE, "release-notes")
        == "# Release notes\n\nGroup the changes by area."
    )


async def test_frontmatter_is_read_as_yaml() -> None:
    service = _service()
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
    assert await service.instructions(ALICE, "tone-guide") == "Be formal."


async def test_uploading_a_skill_of_the_same_name_replaces_it() -> None:
    service = _service()
    first = await service.upload(ALICE, _skill_file(body="old"))

    second = await service.upload(ALICE, _skill_file(body="new"))

    assert second.id == first.id
    assert await service.list_for_user(ALICE) == [second]
    assert await service.instructions(ALICE, "release-notes") == "new"


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
    service = _service()
    skill = await service.upload(ALICE, _skill_file())

    assert await service.list_for_user(BOB) == []
    assert await service.instructions(BOB, "release-notes") is None
    with pytest.raises(SkillNotFoundError):
        await service.delete(BOB, skill.id)

    await service.delete(ALICE, skill.id)
    assert await service.list_for_user(ALICE) == []
