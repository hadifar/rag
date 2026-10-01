import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import SystemMessage
from langgraph.store.base import BaseStore

from rag.domain.errors import InvalidPreferenceError, TooManyPreferencesError
from rag.domain.models import MAX_PREFERENCE_LENGTH, MAX_PREFERENCES, Preference
from rag.services.agent_service.prompts import PREFERENCES_INSTRUCTION


# TODO: must move to somewhere else
@dataclass(frozen=True)
class ChatContext:
    """What a chat turn runs for, set by the caller, never by the model."""

    user_id: uuid.UUID


def _namespace(user_id: uuid.UUID) -> tuple[str, ...]:
    return ("users", str(user_id), "preferences")


async def list_preferences(store: BaseStore, user_id: uuid.UUID) -> list[Preference]:
    """The user's preferences, oldest first."""
    items = await store.asearch(_namespace(user_id), limit=MAX_PREFERENCES)
    return [
        Preference(id=item.key, text=item.value["text"])
        for item in sorted(items, key=lambda item: item.created_at)
    ]


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


async def save_preference(
    store: BaseStore, user_id: uuid.UUID, text: str
) -> Preference:
    """Adds the preference, or returns the same one if the user already has it. Raises
    InvalidPreferenceError if it's blank or too long, TooManyPreferencesError if the
    user is at the cap.
    """
    text = _tidy(text)
    preferences = await list_preferences(store, user_id)
    for preference in preferences:
        if preference.text.casefold() == text.casefold():
            return preference
    if len(preferences) >= MAX_PREFERENCES:
        raise TooManyPreferencesError(MAX_PREFERENCES)

    preference = Preference(id=uuid.uuid4().hex, text=text)
    await store.aput(_namespace(user_id), preference.id, {"text": text})
    return preference


async def delete_preference(
    store: BaseStore, user_id: uuid.UUID, preference_id: str
) -> bool:
    """Whether the user had it. Only ever the user's own: ids are looked up in their
    namespace.
    """
    namespace = _namespace(user_id)
    if await store.aget(namespace, preference_id) is None:
        return False
    await store.adelete(namespace, preference_id)
    return True


def _store(runtime: ToolRuntime[ChatContext]) -> BaseStore:
    if runtime.store is None:
        raise RuntimeError("the agent was built without a store")
    return runtime.store


@tool
async def save_user_preference(text: str, runtime: ToolRuntime[ChatContext]) -> str:
    """Remember a lasting preference the user stated outright about how you answer
    (e.g. language, tone, length, format), in a short sentence. Never save one you only
    inferred.
    """
    try:
        preference = await save_preference(
            _store(runtime), runtime.context.user_id, text
        )
    except (InvalidPreferenceError, TooManyPreferencesError) as exc:
        return f"Not saved: {exc}"
    return f"Saved preference {preference.id}: {preference.text}"


@tool
async def forget_user_preference(
    preference_id: str, runtime: ToolRuntime[ChatContext]
) -> str:
    """Forget one of the user's saved preferences, by its id, when they ask you to."""
    if await delete_preference(_store(runtime), runtime.context.user_id, preference_id):
        return f"Forgot preference {preference_id}."
    return f"No saved preference has the id {preference_id}."


PREFERENCE_TOOLS = (save_user_preference, forget_user_preference)
PREFERENCE_TOOL_NAMES = frozenset(t.name for t in PREFERENCE_TOOLS)


class PreferencesMiddleware(AgentMiddleware[AgentState, ChatContext]):
    """Gives the model the user's saved preferences on every call, read fresh from the
    store, so one saved mid-turn applies from the next call on, plus the tools to save
    and forget them. Added to the call only, never saved to the thread.
    """

    def __init__(self):
        super().__init__()
        self.tools = list(PREFERENCE_TOOLS)

    async def awrap_model_call(
        self,
        request: ModelRequest[ChatContext],
        handler: Callable[[ModelRequest[ChatContext]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        store = request.runtime.store
        if store is None:
            raise RuntimeError("the agent was built without a store")
        preferences = await list_preferences(store, request.runtime.context.user_id)
        saved = (
            "\n".join(f"- [{p.id}] {p.text}" for p in preferences)
            if preferences
            else "(none yet)"
        )
        base = request.system_message.text if request.system_message else ""
        request = request.override(
            system_message=SystemMessage(
                content=f"{base}\n\n{PREFERENCES_INSTRUCTION.format(preferences=saved)}"
            )
        )
        return await handler(request)
