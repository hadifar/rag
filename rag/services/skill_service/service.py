import uuid

from rag.domain.errors import (
    SkillNotFoundError,
    SkillTooLargeError,
    TooManySkillsError,
)
from rag.domain.models import Skill
from rag.domain.ports import SkillRepositoryPort
from rag.services.skill_service.archive import is_archive, read_archive
from rag.services.skill_service.parsing import parse_skill

MAX_SKILL_BYTES = 50 * 1024  # one SKILL.md file
MAX_ARCHIVE_BYTES = 512 * 1024  # a .zip or .skill upload, as uploaded
# Every skill's name and description goes into each of the agent's model calls.
MAX_SKILLS = 20


class SkillService:
    """The skills a user saves: instructions the agent loads, by name, when a request
    fits a skill's description, and reference files it reads when they call for one. A
    user's skills are theirs alone, and apply to every conversation of theirs.
    """

    def __init__(self, skills: SkillRepositoryPort):
        self._skills = skills

    @property
    def max_bytes(self) -> int:
        """No upload larger than this can be accepted."""
        return MAX_ARCHIVE_BYTES

    async def upload(self, user_id: uuid.UUID, data: bytes) -> Skill:
        """Saves a SKILL.md file, or a .zip or .skill archive of one with its reference
        files (see `read_archive`), as a skill, replacing the user's skill of the same
        name if they have one; raises if it isn't a valid skill, is too large, or would
        take them over `MAX_SKILLS`.
        """
        if is_archive(data):
            if len(data) > MAX_ARCHIVE_BYTES:
                raise SkillTooLargeError(MAX_ARCHIVE_BYTES)
            skill_file, files = read_archive(data, MAX_SKILL_BYTES)
        else:
            if len(data) > MAX_SKILL_BYTES:
                raise SkillTooLargeError(MAX_SKILL_BYTES)
            skill_file, files = data, {}
        parsed = parse_skill(skill_file)
        existing = await self._skills.list_for_user(user_id)
        if len(existing) >= MAX_SKILLS and parsed.name not in {
            s.name for s in existing
        }:
            raise TooManySkillsError(MAX_SKILLS)
        return await self._skills.save(
            user_id, parsed.name, parsed.description, parsed.instructions, files
        )

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]:
        """The user's skills, by name."""
        return await self._skills.list_for_user(user_id)

    async def delete(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> None:
        if not await self._skills.delete_owned(user_id, skill_id):
            raise SkillNotFoundError(skill_id)
