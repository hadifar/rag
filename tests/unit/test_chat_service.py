import uuid
from collections.abc import AsyncIterator

import pytest

from rag.domain.errors import ConversationNotFoundError
from rag.domain.models import (
    ArtifactsReady,
    RunContext,
    StreamEvent,
    TextDelta,
    Turn,
)
from rag.services.chat_service.service import ChatService
from tests.unit.fakes import FakeConversationRepository, StubChatAgent

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _service(
    chat_agent: StubChatAgent | None = None,
) -> tuple[ChatService, FakeConversationRepository]:
    repository = FakeConversationRepository()
    service = ChatService(
        repository=repository, rag_service=chat_agent or StubChatAgent()
    )
    return service, repository


async def _chat(
    service: ChatService, conversation_id: uuid.UUID, message: str
) -> list[StreamEvent]:
    return [e async for e in service.send_message(ALICE, conversation_id, message)]


async def test_a_message_moves_the_conversation_to_the_top_of_the_list() -> None:
    service, repository = _service()
    first = await repository.get_or_create_empty(ALICE)
    await repository.set_title(first.id, "first")
    second = await repository.get_or_create_empty(ALICE)
    await repository.set_title(second.id, "second")

    await _chat(service, first.id, "again")

    rows = await repository.list_for_user(ALICE, limit=10, before=None)
    assert [c.title for c in rows] == ["first", "second"]


async def test_each_turn_is_saved_as_it_was_streamed() -> None:
    service, repository = _service(
        StubChatAgent(extra_events=[TextDelta(text="!")], artifacts=[])
    )
    conversation_id = (await repository.get_or_create_empty(ALICE)).id

    streamed = await _chat(service, conversation_id, "hi")
    await _chat(service, conversation_id, "again")

    assert streamed == [
        TextDelta(text="echo: hi"),
        TextDelta(text="!"),
        ArtifactsReady(artifacts=[]),
    ]
    # Saved as the user saw it, the text's deltas merged.
    assert await repository.list_turns(conversation_id) == [
        Turn("hi", [TextDelta(text="echo: hi!"), ArtifactsReady(artifacts=[])]),
        Turn("again", [TextDelta(text="echo: again!"), ArtifactsReady(artifacts=[])]),
    ]


class _FailingChatAgent(StubChatAgent):
    async def stream(self, message: str, ctx: RunContext) -> AsyncIterator[StreamEvent]:
        yield TextDelta(text="half an ans")
        raise RuntimeError("the model went away")


async def test_a_turn_that_fails_midway_is_saved_as_far_as_it_got() -> None:
    service, repository = _service(_FailingChatAgent())
    conversation_id = (await repository.get_or_create_empty(ALICE)).id

    with pytest.raises(RuntimeError):
        await _chat(service, conversation_id, "hi")

    assert await repository.list_turns(conversation_id) == [
        Turn("hi", [TextDelta(text="half an ans")]),
    ]


async def test_sending_to_someone_elses_conversation_is_not_found() -> None:
    service, repository = _service()
    conversation_id = (await repository.get_or_create_empty(BOB)).id

    with pytest.raises(ConversationNotFoundError):
        await _chat(service, conversation_id, "hijack")
    assert await repository.list_turns(conversation_id) == []


async def test_sending_to_a_conversation_that_does_not_exist_is_not_found() -> None:
    service, _ = _service()

    with pytest.raises(ConversationNotFoundError):
        await _chat(service, uuid.uuid4(), "hi")
