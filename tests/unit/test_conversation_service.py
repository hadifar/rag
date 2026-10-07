import uuid
import pytest

from rag.domain.errors import ConversationNotFoundError, InvalidCursorError
from rag.domain.models import (
    ConversationUpdate,
    ArtifactsReady,
    AssistantMessage,
    Conversation,
    StreamEvent,
    TextDelta,
    UserMessage,
)
from rag.services.conversation_service.service import ConversationService
from tests.unit.fakes import (
    FakeConversationRepository,
    StubGeneration,
)

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _service(
    generation: StubGeneration | None = None,
) -> tuple[ConversationService, FakeConversationRepository, StubGeneration]:
    repository = FakeConversationRepository()
    generation = generation or StubGeneration()
    service = ConversationService(repository=repository, llm=generation)
    return service, repository, generation


async def _titled(
    repository: FakeConversationRepository, user_id: uuid.UUID, title: str
) -> Conversation:
    conversation = await repository.get_or_create_empty(user_id)
    await repository.set_title(conversation.id, title)
    return conversation


async def test_create_returns_the_users_one_empty_conversation() -> None:
    service, repository, _ = _service()

    conversation = await service.create(ALICE)

    assert repository.rows[conversation.id].user_id == ALICE
    assert conversation.title is None
    # Until it gets a message, creating again hands back the same one.
    assert (await service.create(ALICE)).id == conversation.id
    await service.generate_title(ALICE, conversation.id, "hi")
    assert (await service.create(ALICE)).id != conversation.id


async def test_generate_title_renames_it_from_the_first_message() -> None:
    service, repository, generation = _service(StubGeneration("Password reset"))
    conversation_id = (await service.create(ALICE)).id

    renamed = await service.generate_title(
        ALICE, conversation_id, "How do I reset my password?"
    )

    assert renamed.title == "Password reset"
    assert repository.rows[conversation_id].title == "Password reset"
    # Needs no answer: nothing was sent to the chat.
    assert "How do I reset my password?" in generation.prompts[0]
    assert await service.history(ALICE, conversation_id) == []


async def test_failed_title_generation_keeps_the_title_from_the_message() -> None:
    service, repository, _ = _service(StubGeneration(error=RuntimeError("LLM down")))
    conversation_id = (await service.create(ALICE)).id
    message = "  How do I\nreset my password?  "

    conversation = await service.generate_title(ALICE, conversation_id, message)

    assert conversation.title == "How do I reset my password?"
    assert repository.rows[conversation_id].title == "How do I reset my password?"


async def test_long_first_message_is_truncated_for_the_fallback_title() -> None:
    service, repository, _ = _service(StubGeneration(error=RuntimeError("LLM down")))
    conversation_id = (await service.create(ALICE)).id

    await service.generate_title(ALICE, conversation_id, "word " * 50)

    title = repository.rows[conversation_id].title
    assert title is not None
    assert len(title) == 60
    assert title.endswith("…")


async def test_cannot_use_a_conversation_someone_else_owns() -> None:
    service, repository, _ = _service()
    conversation_id = (await repository.get_or_create_empty(BOB)).id

    with pytest.raises(ConversationNotFoundError):
        await service.generate_title(ALICE, conversation_id, "hi")
    with pytest.raises(ConversationNotFoundError):
        await service.history(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.delete(ALICE, conversation_id)
    assert repository.rows[conversation_id].title is None
    assert repository.rows[conversation_id].user_id == BOB


async def test_cannot_read_or_delete_a_conversation_that_does_not_exist() -> None:
    service, _, _ = _service()
    conversation_id = uuid.uuid4()

    with pytest.raises(ConversationNotFoundError):
        await service.history(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.delete(ALICE, conversation_id)


async def test_list_pages_through_the_users_conversations_newest_first() -> None:
    service, repository, _ = _service()
    mine = [await _titled(repository, ALICE, f"chat {i}") for i in range(5)]
    await _titled(repository, BOB, "not mine")
    await repository.touch_owned(ALICE, mine[0].id)  # most recently used goes first

    first = await service.list_for_user(ALICE, limit=2, cursor=None)
    second = await service.list_for_user(ALICE, limit=2, cursor=first.next_cursor)
    last = await service.list_for_user(ALICE, limit=2, cursor=second.next_cursor)

    titles = [c.title for page in (first, second, last) for c in page.items]
    assert titles == ["chat 0", "chat 4", "chat 3", "chat 2", "chat 1"]
    assert last.next_cursor is None


async def test_list_has_no_next_page_when_it_fits_exactly() -> None:
    service, repository, _ = _service()
    for i in range(2):
        await _titled(repository, ALICE, f"chat {i}")

    page = await service.list_for_user(ALICE, limit=2, cursor=None)

    assert len(page.items) == 2
    assert page.next_cursor is None


@pytest.mark.parametrize("cursor", ["not-base64!", "bm90IGpzb24=", "WzEsIDJd"])
async def test_list_rejects_a_malformed_cursor(cursor: str) -> None:
    service, _, _ = _service()

    with pytest.raises(InvalidCursorError):
        await service.list_for_user(ALICE, limit=2, cursor=cursor)


async def test_pinned_conversations_leave_the_recent_list_last_pinned_first() -> None:
    service, repository, _ = _service()
    first, second, rest = [
        await _titled(repository, ALICE, f"chat {i}") for i in range(3)
    ]

    await service.update(ALICE, first.id, ConversationUpdate(pinned=True))
    await service.update(ALICE, second.id, ConversationUpdate(pinned=True))

    pinned = await service.list_pinned(ALICE)
    recent = await service.list_for_user(ALICE, limit=10, cursor=None)
    assert [c.id for c in pinned] == [second.id, first.id]
    assert [c.id for c in recent.items] == [rest.id]


async def test_pinning_again_keeps_when_it_was_pinned_and_unpinning_clears_it() -> None:
    service, repository, _ = _service()
    conversation = await _titled(repository, ALICE, "chat")

    pinned = await service.update(
        ALICE, conversation.id, ConversationUpdate(pinned=True)
    )
    again = await service.update(
        ALICE, conversation.id, ConversationUpdate(pinned=True)
    )
    unpinned = await service.update(
        ALICE, conversation.id, ConversationUpdate(pinned=False)
    )

    assert pinned.pinned_at is not None
    assert again.pinned_at == pinned.pinned_at
    assert unpinned.pinned_at is None


async def test_rename_sets_the_title_and_keeps_its_place_and_pin() -> None:
    service, repository, _ = _service()
    conversation = await _titled(repository, ALICE, "chat")
    await service.update(ALICE, conversation.id, ConversationUpdate(pinned=True))
    before = repository.rows[conversation.id]

    renamed = await service.update(
        ALICE, conversation.id, ConversationUpdate(title="Billing")
    )

    assert renamed.title == "Billing"
    assert renamed.updated_at == before.updated_at
    assert renamed.pinned_at == before.pinned_at


async def test_cannot_update_a_conversation_someone_else_owns() -> None:
    service, repository, _ = _service()
    conversation = await _titled(repository, BOB, "bob's")

    with pytest.raises(ConversationNotFoundError):
        await service.update(
            ALICE, conversation.id, ConversationUpdate(title="mine now", pinned=True)
        )
    assert repository.rows[conversation.id].title == "bob's"
    assert repository.rows[conversation.id].pinned_at is None


async def test_delete_removes_the_row_and_its_turns() -> None:
    service, repository, _ = _service()
    conversation_id = (await service.create(ALICE)).id
    await repository.append_turn(
        conversation_id, "hi", [TextDelta(text="hello")], [{"said": "hi"}]
    )

    await service.delete(ALICE, conversation_id)

    assert conversation_id not in repository.rows
    assert await repository.list_turns(conversation_id) == []


async def test_history_is_each_question_then_its_answer() -> None:
    service, repository, _ = _service()
    conversation_id = (await service.create(ALICE)).id
    answer: list[StreamEvent] = [
        TextDelta(text="echo: hi"),
        ArtifactsReady(artifacts=[]),
    ]
    await repository.append_turn(conversation_id, "hi", answer)
    await repository.append_turn(conversation_id, "unanswered", [])

    assert await service.history(ALICE, conversation_id) == [
        UserMessage(text="hi"),
        AssistantMessage(events=answer),
        UserMessage(text="unanswered"),
    ]


async def test_blank_generated_title_falls_back_to_the_message() -> None:
    service, repository, _ = _service(StubGeneration("  \n "))
    conversation_id = (await service.create(ALICE)).id

    renamed = await service.generate_title(ALICE, conversation_id, "question")

    assert renamed.title == "question"
    assert repository.rows[conversation_id].title == "question"
