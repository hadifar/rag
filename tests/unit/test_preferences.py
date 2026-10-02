import uuid

import pytest
from langgraph.store.memory import InMemoryStore

from rag.adapters.lang_preference_store import LangGraphPreferenceRepository
from rag.domain.errors import (
    InvalidPreferenceError,
    PreferenceNotFoundError,
    TooManyPreferencesError,
)
from rag.domain.models import (
    MAX_PREFERENCE_LENGTH,
    MAX_PREFERENCES,
    Preference,
    RunContext,
)
from rag.services.preference_service.service import PreferenceService
from tests.unit.fakes import FakePreferenceRepository

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _service() -> PreferenceService:
    return PreferenceService(FakePreferenceRepository())


async def test_preferences_are_listed_oldest_first_and_per_user() -> None:
    service = _service()
    await service.add(ALICE, "Answer in Dutch")
    await service.add(ALICE, "Keep it short")
    await service.add(BOB, "Be formal")

    assert [p.text for p in await service.list_for_user(ALICE)] == [
        "Answer in Dutch",
        "Keep it short",
    ]
    assert [p.text for p in await service.list_for_user(BOB)] == ["Be formal"]


async def test_saving_the_same_preference_again_keeps_the_one_there_is() -> None:
    service = _service()
    first = await service.add(ALICE, "Answer in Dutch")

    again = await service.add(ALICE, "  answer   in dutch ")

    assert again == first
    assert await service.list_for_user(ALICE) == [first]


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_PREFERENCE_LENGTH + 1)])
async def test_blank_or_too_long_preferences_are_rejected(text: str) -> None:
    with pytest.raises(InvalidPreferenceError):
        await _service().add(ALICE, text)


async def test_a_user_at_the_cap_cant_add_another() -> None:
    service = _service()
    for i in range(MAX_PREFERENCES):
        await service.add(ALICE, f"preference {i}")

    with pytest.raises(TooManyPreferencesError):
        await service.add(ALICE, "one too many")
    assert len(await service.list_for_user(ALICE)) == MAX_PREFERENCES


async def test_a_preference_is_deleted_only_from_its_owner() -> None:
    service = _service()
    preference = await service.add(ALICE, "Answer in Dutch")

    with pytest.raises(PreferenceNotFoundError):
        await service.delete(BOB, preference.id)
    assert await service.list_for_user(ALICE) == [preference]
    await service.delete(ALICE, preference.id)
    assert await service.list_for_user(ALICE) == []


def _ctx(user_id: uuid.UUID) -> RunContext:
    return RunContext(user_id=user_id, conversation_id=uuid.uuid4())


async def test_the_capabilitys_instructions_list_the_users_own_preferences() -> None:
    service = _service()
    mine = await service.add(ALICE, "Answer in Dutch")
    await service.add(BOB, "Answer in French")
    instructions = service.capability().instructions
    assert instructions is not None

    text = await instructions(_ctx(ALICE))

    assert f"- [{mine.id}] Answer in Dutch" in str(text)
    assert "French" not in str(text)
    assert "(none yet)" in str(await instructions(_ctx(uuid.uuid4())))


async def test_the_capabilitys_tools_act_for_the_turns_user() -> None:
    service = _service()
    tools = {tool.name: tool for tool in service.capability().tools}
    assert {tool.kind for tool in tools.values()} == {"user"}

    saved = await tools["save_user_preference"].run("Keep it short", _ctx(ALICE))
    (preference,) = await service.list_for_user(ALICE)
    assert saved.content == f"Saved preference {preference.id}: Keep it short"
    assert saved.references is None  # cites nothing, so the turn has no references

    # Another user can't forget it: their ids are looked up among their own.
    forgot = await tools["forget_user_preference"].run(preference.id, _ctx(BOB))
    assert forgot.content == f"No saved preference has the id {preference.id}."
    forgot = await tools["forget_user_preference"].run(preference.id, _ctx(ALICE))
    assert forgot.content == f"Forgot preference {preference.id}."
    assert await service.list_for_user(ALICE) == []


async def test_a_rejected_preference_is_reported_to_the_model_not_raised() -> None:
    save = _service().capability().tools[0]

    result = await save.run("   ", _ctx(ALICE))

    assert result.content.startswith("Not saved: Invalid preference")


async def test_the_langgraph_repository_keeps_each_users_own_oldest_first() -> None:
    repository = LangGraphPreferenceRepository(InMemoryStore())
    first, second = Preference("a", "Answer in Dutch"), Preference("b", "Be brief")
    await repository.add(ALICE, first)
    await repository.add(ALICE, second)

    assert await repository.list_for_user(ALICE) == [first, second]
    assert await repository.list_for_user(BOB) == []
    assert not await repository.delete(BOB, first.id)
    assert await repository.delete(ALICE, first.id)
    assert await repository.list_for_user(ALICE) == [second]


async def test_the_langgraph_repository_lists_up_to_the_cap() -> None:
    # The store's search returns 10 items by default; a user may have more.
    repository = LangGraphPreferenceRepository(InMemoryStore())
    for i in range(MAX_PREFERENCES):
        await repository.add(ALICE, Preference(str(i), f"preference {i}"))

    assert len(await repository.list_for_user(ALICE)) == MAX_PREFERENCES
