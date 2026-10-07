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

# Every skill's name and description goes into each of the agent's model calls.
MAX_SKILLS = 20


class SkillService:
    """The skills a user saves: instructions the agent loads, by name, when a request
    fits a skill's description, and reference files it reads when they call for one. A
    user's skills are theirs alone, and apply to every conversation of theirs.
    """

    def __init__(
        self,
        skills: SkillRepositoryPort,
        *,
        max_skill_bytes: int,
        max_archive_bytes: int,
    ):
        """A SKILL.md file, alone or in an archive, may be up to `max_skill_bytes`; a
        .zip or .skill archive, as uploaded, up to `max_archive_bytes`.
        """
        self._skills = skills
        self._max_skill_bytes = max_skill_bytes
        self._max_archive_bytes = max_archive_bytes

    async def upload(self, user_id: uuid.UUID, data: bytes) -> Skill:
        """Saves a SKILL.md file, or a .zip or .skill archive of one with its reference
        files (see `read_archive`), as a skill, replacing the user's skill of the same
        name if they have one; raises if it isn't a valid skill, is too large, or would
        take them over `MAX_SKILLS`.
        """
        if is_archive(data):
            if len(data) > self._max_archive_bytes:
                raise SkillTooLargeError(self._max_archive_bytes)
            skill_file, files = read_archive(data, self._max_skill_bytes)
        else:
            if len(data) > self._max_skill_bytes:
                raise SkillTooLargeError(self._max_skill_bytes)
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
