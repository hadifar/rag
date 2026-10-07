import uuid
from collections.abc import Mapping
from typing import Protocol

from rag.domain.models import Skill, SkillContent


class SkillRepositoryPort(Protocol):
    """The skills users save, each theirs alone."""

    async def save(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str,
        instructions: str,
        files: Mapping[str, str],
    ) -> Skill:
        """Saves it with its reference `files` (content by path), replacing the user's
        skill of that name, files and all, if they have one.
        """
        ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]:
        """The user's skills, by name."""
        ...

    async def get_content(self, user_id: uuid.UUID, name: str) -> SkillContent | None:
        """None if the user has no skill of that name."""
        ...

    async def get_file(self, user_id: uuid.UUID, name: str, path: str) -> str | None:
        """The content of a reference file of the user's skill of that name; None if
        they have no such skill, or it no such file.
        """
        ...

    async def delete_owned(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        """Deletes it if it's the user's; whether it was."""
        ...


class SkillsPort(Protocol):
    """The skills the agent may use for a user (see `SkillService`)."""

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]: ...

    async def content(self, user_id: uuid.UUID, name: str) -> SkillContent | None:
        """The user's skill of that name; None if they have none."""
        ...

    async def file(self, user_id: uuid.UUID, name: str, path: str) -> str | None:
        """A reference file of the user's skill of that name; None if there's none."""
        ...
