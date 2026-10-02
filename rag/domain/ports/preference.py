import uuid
from typing import Protocol

from rag.domain.models import Preference


class PreferenceRepositoryPort(Protocol):
    """Each user's preferences, as they're kept: the rules on what may be kept are the
    preference service's.
    """

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        """Oldest first."""
        ...

    async def add(self, user_id: uuid.UUID, preference: Preference) -> None: ...
    async def delete(self, user_id: uuid.UUID, preference_id: str) -> bool:
        """Whether the user had it. Only ever the user's own: another user's id is
        as good as a missing one.
        """
        ...
