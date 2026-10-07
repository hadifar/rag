import uuid
from typing import Protocol

from rag.domain.models import Skill


class SkillRepositoryPort(Protocol):
    """The skills users save, each theirs alone."""

    async def save(
        self, user_id: uuid.UUID, name: str, description: str, instructions: str
    ) -> Skill:
        """Saves it, replacing the user's skill of that name if they have one."""
        ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]:
        """The user's skills, by name."""
        ...

    async def get_instructions(self, user_id: uuid.UUID, name: str) -> str | None:
        """None if the user has no skill of that name."""
        ...

    async def delete_owned(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        """Deletes it if it's the user's; whether it was."""
        ...


class SkillsPort(Protocol):
    """The skills the agent may use for a user (see `SkillService`)."""

    async def list_for_user(self, user_id: uuid.UUID) -> list[Skill]: ...

    async def instructions(self, user_id: uuid.UUID, name: str) -> str | None:
        """The instructions of the user's skill of that name; None if they have none."""
        ...
