import uuid
from collections.abc import AsyncIterator, Sequence

import pytest

from rag.domain.errors import ConversationNotFoundError
from rag.domain.models import (
    ConversationUpdate,
    AgentMemory,
    ArtifactsReady,
    AttachmentFile,
    RunContext,
    StreamEvent,
    TextDelta,
    Turn,
)
from rag.services.chat_service.service import ChatService
from tests.unit.fakes import (
    FakeAttachmentRepository,
    FakeConversationRepository,
    StubAgent,
    StubTurn,
)

ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def _service(
    agent: StubAgent | None = None,
) -> tuple[ChatService, FakeConversationRepository]:
    repository = FakeConversationRepository()
    service = ChatService(
        repository=repository,
        attachments=FakeAttachmentRepository(repository),
        agent=agent or StubAgent(),
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
        StubAgent(extra_events=[TextDelta(text="!")], artifacts=[])
    )
    conversation_id = (await repository.get_or_create_empty(ALICE)).id

    streamed = await _chat(service, conversation_id, "hi")
    await _chat(service, conversation_id, "again")

    assert streamed == [
        TextDelta(text="echo: hi"),
        TextDelta(text="!"),
        ArtifactsReady(artifacts=[]),
    ]
    # Saved as the user saw it, the text's deltas merged, beside the agent's memory.
    assert await repository.list_turns(conversation_id) == [
        Turn(
            "hi",
            [TextDelta(text="echo: hi!"), ArtifactsReady(artifacts=[])],
            [{"said": "hi"}],
        ),
        Turn(
            "again",
            [TextDelta(text="echo: again!"), ArtifactsReady(artifacts=[])],
            [{"said": "again"}],
        ),
    ]


async def test_the_agent_is_given_its_memory_of_the_earlier_turns() -> None:
    agent = StubAgent()
    service, repository = _service(agent)
    conversation_id = (await repository.get_or_create_empty(ALICE)).id
    # A turn the agent forgot (blocked, failed) is no part of its memory.
    await repository.append_turn(conversation_id, "blocked", [], None)

    await _chat(service, conversation_id, "first")
    await _chat(service, conversation_id, "second")

    assert agent.histories == [[], [[{"said": "first"}]]]


class _FailingTurn(StubTurn):
    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        yield TextDelta(text="half an ans")
        raise RuntimeError("the model went away")


class _FailingAgent(StubAgent):
    def stream(
        self,
        message: str,
        history: Sequence[AgentMemory],
        ctx: RunContext,
        *,
        attachments: Sequence[AttachmentFile] = (),
        earlier_attachments: Sequence[AttachmentFile] = (),
    ) -> StubTurn:
        return _FailingTurn([], [{"said": message}])


async def test_a_turn_that_fails_midway_is_saved_as_far_as_it_got() -> None:
    service, repository = _service(_FailingAgent())
    conversation_id = (await repository.get_or_create_empty(ALICE)).id

    with pytest.raises(RuntimeError):
        await _chat(service, conversation_id, "hi")

    # Kept as far as the user saw it; the agent forgets it.
    assert await repository.list_turns(conversation_id) == [
        Turn("hi", [TextDelta(text="half an ans")], None),
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


async def test_attachments_go_to_the_agent_and_are_saved_with_their_turn() -> None:
    agent = StubAgent()
    service, repository = _service(agent)
    conversation_id = (await repository.get_or_create_empty(ALICE)).id
    await FakeAttachmentRepository(repository).create(
        conversation_id, "error.png", "image/png", b"png"
    )
    [file] = repository.attachments.values()

    [_ async for _ in service.send_message(ALICE, conversation_id, "", [file])]
    await _chat(service, conversation_id, "and now?")

    assert agent.attachments == [[file], []]
    # The second turn reads the first one's attachment again.
    assert agent.earlier_attachments == [[], [file]]
    turns = await repository.list_turns(conversation_id)
    assert [t.attachments for t in turns] == [[file.attachment], []]


async def test_a_turn_runs_on_the_model_and_effort_its_conversation_is_set_to() -> None:
    agent = StubAgent()
    service, repository = _service(agent)
    conversation_id = (await repository.get_or_create_empty(ALICE)).id

    await _chat(service, conversation_id, "hi")
    await repository.update_owned(
        ALICE, conversation_id, ConversationUpdate(model="gpt-6-sol", effort="high")
    )
    await _chat(service, conversation_id, "again")

    assert [(c.model, c.effort) for c in agent.contexts] == [
        ("gpt-6-luna", "low"),
        ("gpt-6-sol", "high"),
    ]
