import uuid

import pytest
from langgraph.store.memory import InMemoryStore

from rag.domain.errors import InvalidPreferenceError, TooManyPreferencesError
from rag.domain.models import MAX_PREFERENCE_LENGTH, MAX_PREFERENCES
from rag.services.agent_service.memory_store.preferences import (
    delete_preference,
    list_preferences,
    save_preference,
)

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


async def test_preferences_are_listed_oldest_first_and_per_user() -> None:
    store = InMemoryStore()
    await save_preference(store, ALICE, "Answer in Dutch")
    await save_preference(store, ALICE, "Keep it short")
    await save_preference(store, BOB, "Be formal")

    assert [p.text for p in await list_preferences(store, ALICE)] == [
        "Answer in Dutch",
        "Keep it short",
    ]
    assert [p.text for p in await list_preferences(store, BOB)] == ["Be formal"]


async def test_saving_the_same_preference_again_keeps_the_one_there_is() -> None:
    store = InMemoryStore()
    first = await save_preference(store, ALICE, "Answer in Dutch")

    again = await save_preference(store, ALICE, "  answer   in dutch ")

    assert again == first
    assert await list_preferences(store, ALICE) == [first]


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_PREFERENCE_LENGTH + 1)])
async def test_blank_or_too_long_preferences_are_rejected(text: str) -> None:
    with pytest.raises(InvalidPreferenceError):
        await save_preference(InMemoryStore(), ALICE, text)


async def test_a_user_at_the_cap_cant_add_another() -> None:
    store = InMemoryStore()
    for i in range(MAX_PREFERENCES):
        await save_preference(store, ALICE, f"preference {i}")

    with pytest.raises(TooManyPreferencesError):
        await save_preference(store, ALICE, "one too many")
    assert len(await list_preferences(store, ALICE)) == MAX_PREFERENCES


async def test_a_preference_is_deleted_only_from_its_owner() -> None:
    store = InMemoryStore()
    preference = await save_preference(store, ALICE, "Answer in Dutch")

    assert not await delete_preference(store, BOB, preference.id)
    assert await list_preferences(store, ALICE) == [preference]
    assert await delete_preference(store, ALICE, preference.id)
    assert await list_preferences(store, ALICE) == []
