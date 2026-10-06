import uuid

from rag.domain.errors import (
    InvalidPreferenceError,
    PreferenceNotFoundError,
    TooManyPreferencesError,
)
from rag.domain.models import MAX_PREFERENCE_LENGTH, MAX_PREFERENCES, Preference
from rag.domain.ports import PreferenceRepositoryPort


class PreferenceService:
    """What each user wants of every answer: kept per user, across all their
    conversations (a PreferencesPort). The user manages them through the API, and the
    chat agent through its preference tools.
    """

    def __init__(self, repository: PreferenceRepositoryPort):
        self._repository = repository

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        """Oldest first."""
        return await self._repository.list_for_user(user_id)

    async def add(self, user_id: uuid.UUID, text: str) -> Preference:
        """The saved preference, or the same one if the user already has it (ignoring
        case and spacing). Raises InvalidPreferenceError if it's blank or too long,
        TooManyPreferencesError if the user has the most allowed.
        """
        text = _tidy(text)
        preferences = await self._repository.list_for_user(user_id)
        for preference in preferences:
            if preference.text.casefold() == text.casefold():
                return preference
        if len(preferences) >= MAX_PREFERENCES:
            raise TooManyPreferencesError(MAX_PREFERENCES)

        return await self._repository.add(
            user_id, Preference(id=uuid.uuid4().hex, text=text)
        )

    async def delete(self, user_id: uuid.UUID, preference_id: str) -> None:
        """Raises PreferenceNotFoundError if the user has no preference with that id."""
        if not await self._repository.delete(user_id, preference_id):
            raise PreferenceNotFoundError(preference_id)


def _tidy(text: str) -> str:
    """`text` with its whitespace collapsed; raises InvalidPreferenceError if that's
    blank or too long.
    """
    text = " ".join(text.split())
    if not text:
        raise InvalidPreferenceError("it is blank")
    if len(text) > MAX_PREFERENCE_LENGTH:
        raise InvalidPreferenceError(
            f"it is longer than {MAX_PREFERENCE_LENGTH} characters"
        )
    return text
