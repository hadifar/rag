import uuid

import pytest

from rag.domain.errors import ConversationNotFoundError, InvalidCursorError
from rag.domain.models import Conversation
from rag.services.conversation_service.service import ConversationService
from tests.unit.fakes import FakeConversationRepository, StubGeneration, StubRag

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _service(
    generation: StubGeneration | None = None,
) -> tuple[ConversationService, FakeConversationRepository, StubGeneration]:
    repository = FakeConversationRepository()
    generation = generation or StubGeneration()
    service = ConversationService(repository=repository, agent_service=generation)
    return service, repository, generation


async def _titled(
    repository: FakeConversationRepository, user_id: uuid.UUID, title: str
) -> Conversation:
    conversation = await repository.get_or_create_empty(user_id)
    await repository.set_title(conversation.id, title)
    return conversation


async def _chat(
    generation: StubGeneration, conversation_id: uuid.UUID, message: str
) -> None:
    """Has the RAG chat answer in the thread, as the router does; the service isn't
    involved in a turn, only in reading what it saved.
    """
    rag = StubRag(generation.threads)
    _ = [e async for e in rag.stream_chat(message, str(conversation_id), ALICE)]


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
    assert generation.threads == {}


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
    assert title is not None and len(title) == 60
    assert title.endswith("…")


async def test_touch_moves_the_conversation_to_the_top_of_the_list() -> None:
    service, repository, _ = _service()
    first = await _titled(repository, ALICE, "first")
    await _titled(repository, ALICE, "second")

    await service.touch(ALICE, first.id)

    page = await service.list_for_user(ALICE, limit=10, cursor=None)
    assert [c.title for c in page.items] == ["first", "second"]


async def test_cannot_use_a_conversation_someone_else_owns() -> None:
    service, repository, generation = _service()
    conversation_id = (await repository.get_or_create_empty(BOB)).id

    with pytest.raises(ConversationNotFoundError):
        await service.touch(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.generate_title(ALICE, conversation_id, "hi")
    with pytest.raises(ConversationNotFoundError):
        await service.history(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.delete(ALICE, conversation_id)
    assert generation.threads == {}
    assert repository.rows[conversation_id].title is None
    assert generation.deleted_threads == []
    assert repository.rows[conversation_id].user_id == BOB


async def test_cannot_read_or_delete_a_conversation_that_does_not_exist() -> None:
    service, _, generation = _service()
    conversation_id = uuid.uuid4()

    with pytest.raises(ConversationNotFoundError):
        await service.touch(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.history(ALICE, conversation_id)
    with pytest.raises(ConversationNotFoundError):
        await service.delete(ALICE, conversation_id)
    assert generation.deleted_threads == []


async def test_list_pages_through_the_users_conversations_newest_first() -> None:
    service, repository, _ = _service()
    mine = [await _titled(repository, ALICE, f"chat {i}") for i in range(5)]
    await _titled(repository, BOB, "not mine")
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
        await _titled(repository, ALICE, f"chat {i}")

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
    conversation_id = (await service.create(ALICE)).id
    await _chat(generation, conversation_id, "hi")

    await service.delete(ALICE, conversation_id)

    assert generation.deleted_threads == [str(conversation_id)]
    assert conversation_id not in repository.rows


async def test_history_returns_the_threads_messages() -> None:
    service, _, generation = _service()
    conversation_id = (await service.create(ALICE)).id
    await _chat(generation, conversation_id, "hi")

    history = await service.history(ALICE, conversation_id)

    assert [(m.role, m.text) for m in history] == [
        ("user", "hi"),
        ("assistant", "echo: hi"),
    ]


async def test_blank_generated_title_falls_back_to_the_message() -> None:
    service, repository, _ = _service(StubGeneration("  \n "))
    conversation_id = (await service.create(ALICE)).id

    renamed = await service.generate_title(ALICE, conversation_id, "question")

    assert renamed.title == "question"
    assert repository.rows[conversation_id].title == "question"
