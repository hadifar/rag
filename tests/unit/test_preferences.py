import uuid

import pytest

from rag.domain.errors import (
    InvalidPreferenceError,
    PreferenceNotFoundError,
    TooManyPreferencesError,
)
from rag.domain.models import MAX_PREFERENCE_LENGTH, MAX_PREFERENCES
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
