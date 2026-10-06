import uuid
from typing import Protocol

from rag.domain.models import Preference


class PreferencesPort(Protocol):
    """Each user's preferences, with the rules on what may be kept: what the chat
    agent's preference tools and instructions go through.
    """

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        """Oldest first."""
        ...

    async def add(self, user_id: uuid.UUID, text: str) -> Preference:
        """The saved preference, or the same one if the user already has it. Raises
        InvalidPreferenceError if it's blank or too long, TooManyPreferencesError if
        the user has the most allowed.
        """
        ...

    async def delete(self, user_id: uuid.UUID, preference_id: str) -> None:
        """Raises PreferenceNotFoundError if the user has no preference with that id."""
        ...


class PreferenceRepositoryPort(Protocol):
    """Each user's preferences, as they're kept. The preference service applies the
    rules on what may be kept; the store backs up the two a race could slip past.
    """

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        """Oldest first."""
        ...

    async def add(self, user_id: uuid.UUID, preference: Preference) -> Preference:
        """What the user now has: `preference`, or their own with the same text
        (ignoring case) if one was added meanwhile. Raises TooManyPreferencesError if
        they already have the most allowed.
        """
        ...

    async def delete(self, user_id: uuid.UUID, preference_id: str) -> bool:
        """Whether the user had it. Only ever the user's own: another user's id is
        as good as a missing one.
        """
        ...
