import uuid

from rag.domain.errors import (
    InvalidPreferenceError,
    PreferenceNotFoundError,
    TooManyPreferencesError,
)
from rag.domain.models import (
    MAX_PREFERENCE_LENGTH,
    MAX_PREFERENCES,
    Capability,
    Preference,
    RunContext,
    Tool,
    ToolResult,
)
from rag.domain.ports import PreferenceRepositoryPort
from rag.services.preference_service.prompts import (
    FORGET_TOOL_DESCRIPTION,
    PREFERENCES_INSTRUCTION,
    SAVE_TOOL_DESCRIPTION,
)


class PreferenceService:
    """What each user wants of every answer: kept per user, across all their
    conversations. The user manages them through the API, and a chat agent through the
    `capability` it's given: the preferences in each model call's instructions, and
    tools to save and forget them.
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

    def capability(self) -> Capability:
        return Capability(
            tools=[
                Tool(
                    name="save_user_preference",
                    description=SAVE_TOOL_DESCRIPTION,
                    run=self._save,
                    kind="user",
                    parameter="text",
                ),
                Tool(
                    name="forget_user_preference",
                    description=FORGET_TOOL_DESCRIPTION,
                    run=self._forget,
                    kind="user",
                    parameter="preference_id",
                ),
            ],
            instructions=self._instructions,
        )

    async def _instructions(self, ctx: RunContext) -> str:
        preferences = await self.list_for_user(ctx.user_id)
        saved = "\n".join(f"- [{p.id}] {p.text}" for p in preferences) or "(none yet)"
        return PREFERENCES_INSTRUCTION.format(preferences=saved)

    async def _save(self, text: str, ctx: RunContext) -> ToolResult:
        try:
            preference = await self.add(ctx.user_id, text)
        except (InvalidPreferenceError, TooManyPreferencesError) as exc:
            return ToolResult(f"Not saved: {exc}")
        return ToolResult(f"Saved preference {preference.id}: {preference.text}")

    async def _forget(self, preference_id: str, ctx: RunContext) -> ToolResult:
        try:
            await self.delete(ctx.user_id, preference_id)
        except PreferenceNotFoundError:
            return ToolResult(f"No saved preference has the id {preference_id}.")
        return ToolResult(f"Forgot preference {preference_id}.")


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
