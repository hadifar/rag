"""Runs the attachment SQL against real Postgres (migrated with `alembic upgrade head`).
Each test works under its own throwaway user; deleting it cascades to its
conversations, and from them to their turns and attachments.
"""

import hashlib
import uuid
from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.config import Settings
from rag.domain.models import Conversation, TextDelta
from rag.repository.attachment_repository import AttachmentRepository
from rag.repository.conversation_repository import ConversationRepository

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16


@pytest.fixture
async def pool(
    integration_settings: Settings,
) -> AsyncGenerator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool[AsyncConnection](
        integration_settings.DATABASE_URL.get_secret_value(), open=False
    ) as pool:
        yield pool


@pytest.fixture
async def conversation(
    pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[Conversation]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, 'x') RETURNING id",
            (f"attachment-test-{uuid.uuid4()}@example.com",),
        )
        row = await cur.fetchone()
        assert row is not None
    yield await ConversationRepository(pool).get_or_create_empty(row[0])
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM users WHERE id = %s", (row[0],))


async def test_an_attachment_is_kept_with_its_content(
    pool: AsyncConnectionPool[AsyncConnection], conversation: Conversation
) -> None:
    attachments = AttachmentRepository(pool)

    attachment = await attachments.create(conversation.id, "a.png", "image/png", PNG)

    assert attachment.size == len(PNG)
    assert attachment.sha256 == hashlib.sha256(PNG).hexdigest()
    file = await attachments.get_owned(
        conversation.user_id, conversation.id, attachment.id
    )
    assert file is not None
    assert (file.attachment, file.data) == (attachment, PNG)
    # Another user's lookup finds nothing.
    assert (
        await attachments.get_owned(uuid.uuid4(), conversation.id, attachment.id)
        is None
    )


async def test_a_turn_lists_its_attachments_in_the_order_sent(
    pool: AsyncConnectionPool[AsyncConnection], conversation: Conversation
) -> None:
    attachments = AttachmentRepository(pool)
    conversations = ConversationRepository(pool)
    first = await attachments.create(conversation.id, "a.png", "image/png", PNG)
    second = await attachments.create(conversation.id, "b.md", "text/markdown", b"# B")
    stranger = uuid.uuid4()  # in no conversation: not linked

    await conversations.append_turn(
        conversation.id,
        "",
        [TextDelta(text="ok")],
        attachment_ids=[second.id, stranger, first.id],
    )
    # A retry sends the same attachment with another turn.
    await conversations.append_turn(
        conversation.id, "again", [], attachment_ids=[second.id]
    )

    turns = await conversations.list_turns(conversation.id)
    assert [t.attachments for t in turns] == [[second, first], [second]]
    in_order = await attachments.list_in(conversation.id, [second.id, first.id])
    assert [f.attachment for f in in_order] == [second, first]
    sent = await attachments.list_sent(conversation.id)
    assert {f.attachment.id for f in sent} == {first.id, second.id}


async def test_only_unsent_attachments_are_deleted(
    pool: AsyncConnectionPool[AsyncConnection], conversation: Conversation
) -> None:
    attachments = AttachmentRepository(pool)
    sent = await attachments.create(conversation.id, "a.png", "image/png", PNG)
    unsent = await attachments.create(conversation.id, "b.png", "image/png", PNG)
    await ConversationRepository(pool).append_turn(
        conversation.id, "q", [], attachment_ids=[sent.id]
    )

    assert not await attachments.delete_unsent(conversation.id, sent.id)
    assert await attachments.delete_unsent(conversation.id, unsent.id)
    assert await attachments.list_in(conversation.id, [sent.id, unsent.id]) != []
