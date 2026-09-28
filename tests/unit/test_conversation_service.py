import uuid
from typing import cast

import pytest

from rag.domain.errors import ConversationNotFoundError, InvalidCursorError
from rag.domain.events import (
    ConversationReady,
    ConversationTitled,
    StreamEvent,
    TextDelta,
)
from rag.services.conversation_service.service import ConversationService
from tests.unit.fakes import FakeConversationRepository, StubGeneration

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _service(
    generation: StubGeneration | None = None,
) -> tuple[ConversationService, FakeConversationRepository, StubGeneration]:
    repository = FakeConversationRepository()
    generation = generation or StubGeneration()
    service = ConversationService(repository=repository, generation=generation)
    return service, repository, generation


async def _send(
    service: ConversationService,
    user_id: uuid.UUID,
    message: str,
    conversation_id: uuid.UUID | None = None,
) -> list[StreamEvent]:
    turn = await service.start_turn(user_id, conversation_id, message)
    return [event async for event in service.stream_turn(turn, message)]


async def test_first_message_creates_a_conversation_owned_by_the_sender() -> None:
    service, repository, _ = _service()

    events = await _send(service, ALICE, "How do I reset my password?")

    assert isinstance(events[0], ConversationReady)
    created = repository.rows[events[0].conversation.id]
    assert created.user_id == ALICE


async def test_new_conversation_gets_a_generated_title_as_the_last_event() -> None:
    service, repository, generation = _service(StubGeneration(title="Password reset"))

    events = await _send(service, ALICE, "How do I reset my password?")

    conversation_id = cast(ConversationReady, events[0]).conversation.id
    assert events[-1] == ConversationTitled(
        conversation_id=str(conversation_id), title="Password reset"
    )
    assert repository.rows[conversation_id].title == "Password reset"
    # The title is generated from both sides of the first exchange.
    assert generation.title_requests == [
        ("How do I reset my password?", "echo: How do I reset my password?")
    ]


async def test_failed_title_generation_keeps_the_fallback_title() -> None:
    service, repository, _ = _service(StubGeneration(title=None))

    events = await _send(service, ALICE, "  How do I\nreset my password?  ")

    assert not any(isinstance(e, ConversationTitled) for e in events)
    assert [e for e in events if isinstance(e, TextDelta)]  # the answer still streamed
    (conversation,) = repository.rows.values()
    assert conversation.title == "How do I reset my password?"


async def test_long_first_message_is_truncated_for_the_fallback_title() -> None:
    service, repository, _ = _service(StubGeneration(title=None))

    await _send(service, ALICE, "word " * 50)

    (conversation,) = repository.rows.values()
    assert len(conversation.title) == 60
    assert conversation.title.endswith("…")


async def test_follow_up_message_reuses_the_conversation_and_is_not_retitled() -> None:
    service, repository, generation = _service()
    first = await _send(service, ALICE, "first")
    conversation_id = cast(ConversationReady, first[0]).conversation.id

    second = await _send(service, ALICE, "second", conversation_id)

    assert cast(ConversationReady, second[0]).conversation.id == conversation_id
    assert not any(isinstance(e, ConversationTitled) for e in second)
    assert len(generation.title_requests) == 1
    assert len(repository.rows) == 1
    assert len(generation.threads[str(conversation_id)]) == 4


async def test_first_message_with_a_client_id_creates_the_conversation_under_it() -> (
    None
):
    service, repository, _ = _service()
    client_id = uuid.uuid4()

    events = await _send(service, ALICE, "hi", client_id)

    assert cast(ConversationReady, events[0]).conversation.id == client_id
    assert repository.rows[client_id].user_id == ALICE
    assert isinstance(events[-1], ConversationTitled)  # titled like any new chat


async def test_cannot_use_a_conversation_someone_else_owns() -> None:
    service, repository, generation = _service()
    conversation_id = (await repository.create(BOB, "Bob's chat")).id

    with pytest.raises(ConversationNotFoundError):
        await service.start_turn(ALICE, conversation_id, "hi")
    with pytest.raises(ConversationNotFoundError):
        await service.history(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.delete(ALICE, conversation_id)
    assert generation.deleted_threads == []
    assert repository.rows[conversation_id].user_id == BOB


async def test_cannot_read_or_delete_a_conversation_that_does_not_exist() -> None:
    service, _, generation = _service()
    conversation_id = uuid.uuid4()

    with pytest.raises(ConversationNotFoundError):
        await service.history(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.delete(ALICE, conversation_id)
    assert generation.deleted_threads == []


async def test_list_pages_through_the_users_conversations_newest_first() -> None:
    service, repository, _ = _service()
    mine = [await repository.create(ALICE, f"chat {i}") for i in range(5)]
    await repository.create(BOB, "not mine")
    await repository.touch(mine[0].id)  # most recently used goes first

    first = await service.list_for_user(ALICE, limit=2, cursor=None)
    second = await service.list_for_user(ALICE, limit=2, cursor=first.next_cursor)
    last = await service.list_for_user(ALICE, limit=2, cursor=second.next_cursor)

    titles = [c.title for page in (first, second, last) for c in page.items]
    assert titles == ["chat 0", "chat 4", "chat 3", "chat 2", "chat 1"]
    assert last.next_cursor is None


async def test_list_has_no_next_page_when_it_fits_exactly() -> None:
    service, repository, _ = _service()
    for i in range(2):
        await repository.create(ALICE, f"chat {i}")

    page = await service.list_for_user(ALICE, limit=2, cursor=None)

    assert len(page.items) == 2
    assert page.next_cursor is None


@pytest.mark.parametrize("cursor", ["not-base64!", "bm90IGpzb24=", "WzEsIDJd"])
async def test_list_rejects_a_malformed_cursor(cursor: str) -> None:
    service, _, _ = _service()

    with pytest.raises(InvalidCursorError):
        await service.list_for_user(ALICE, limit=2, cursor=cursor)


async def test_delete_removes_the_messages_and_the_conversation() -> None:
    service, repository, generation = _service()
    events = await _send(service, ALICE, "hi")
    conversation_id = cast(ConversationReady, events[0]).conversation.id

    await service.delete(ALICE, conversation_id)

    assert generation.deleted_threads == [str(conversation_id)]
    assert conversation_id not in repository.rows


async def test_history_returns_the_threads_messages() -> None:
    service, _, _ = _service()
    events = await _send(service, ALICE, "hi")
    conversation_id = cast(ConversationReady, events[0]).conversation.id

    history = await service.history(ALICE, conversation_id)

    assert [(m.role, m.text) for m in history] == [
        ("user", "hi"),
        ("assistant", "echo: hi"),
    ]
