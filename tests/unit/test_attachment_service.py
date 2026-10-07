import uuid
from datetime import timedelta

import pytest

from rag.domain.errors import (
    AttachmentNotFoundError,
    AttachmentTooLargeError,
    ConversationNotFoundError,
    UnsupportedAttachmentError,
)
from rag.domain.models import TextDelta
from rag.services.attachment_service.service import AttachmentService
from tests.unit.fakes import FakeAttachmentRepository, FakeConversationRepository

ALICE = uuid.uuid4()
BOB = uuid.uuid4()

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 16
MARKDOWN = "# Notes\n\nÜber die Synchronisierung.".encode()


async def _setup() -> tuple[AttachmentService, FakeConversationRepository, uuid.UUID]:
    conversations = FakeConversationRepository()
    service = AttachmentService(
        attachments=FakeAttachmentRepository(conversations),
        conversations=conversations,
    )
    conversation = await conversations.get_or_create_empty(ALICE)
    return service, conversations, conversation.id


@pytest.mark.parametrize(
    ("name", "data", "media_type"),
    [
        ("notes.md", MARKDOWN, "text/markdown"),
        ("NOTES.MARKDOWN", MARKDOWN, "text/markdown"),
        ("photo.png", PNG, "image/png"),
        ("photo.jpg", JPEG, "image/jpeg"),
        # An image is told by its content, whatever its name says.
        ("photo.jpeg.txt", PNG, "image/png"),
    ],
)
async def test_an_upload_is_recognized_by_its_content(
    name: str, data: bytes, media_type: str
) -> None:
    service, _, conversation_id = await _setup()

    attachment = await service.upload(ALICE, conversation_id, name, data)

    assert attachment.media_type == media_type
    assert attachment.size == len(data)
    file = await service.get(ALICE, conversation_id, attachment.id)
    assert file.data == data


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("notes.txt", b"plain text"),  # text, but not markdown
        ("notes.md", b"\xff\xfe binary"),  # not UTF-8
        ("notes.md", b"text\0with a NUL"),
        ("photo.png", b"GIF89a"),  # an image of another format
        ("notes.md", b""),
    ],
)
async def test_other_files_are_rejected(name: str, data: bytes) -> None:
    service, _, conversation_id = await _setup()

    with pytest.raises(UnsupportedAttachmentError, match=r"\.md, \.png, \.jpg"):
        await service.upload(ALICE, conversation_id, name, data)


async def test_a_file_over_its_kinds_limit_is_rejected() -> None:
    service, _, conversation_id = await _setup()
    # Fine for an image, but too much text.
    big_markdown = b"#" * (200 * 1024 + 1)

    with pytest.raises(AttachmentTooLargeError, match="200 KB"):
        await service.upload(ALICE, conversation_id, "big.md", big_markdown)
    assert service.max_bytes == 5 * 1024 * 1024


async def test_the_name_is_kept_without_its_directories() -> None:
    service, _, conversation_id = await _setup()

    attachment = await service.upload(
        ALICE, conversation_id, "C:\\Users\\me\\..\\notes\n.md", MARKDOWN
    )

    assert attachment.name == "notes .md"


async def test_only_the_owner_can_upload_or_read_attachments() -> None:
    service, _, conversation_id = await _setup()
    attachment = await service.upload(ALICE, conversation_id, "a.png", PNG)

    with pytest.raises(ConversationNotFoundError):
        await service.upload(BOB, conversation_id, "b.png", PNG)
    with pytest.raises(AttachmentNotFoundError):
        await service.get(BOB, conversation_id, attachment.id)


async def test_attachments_to_send_come_in_the_order_given() -> None:
    service, _, conversation_id = await _setup()
    first = await service.upload(ALICE, conversation_id, "a.png", PNG)
    second = await service.upload(ALICE, conversation_id, "b.md", MARKDOWN)

    files = await service.to_send(ALICE, conversation_id, [second.id, first.id])

    assert [f.attachment for f in files] == [second, first]


async def test_an_attachment_of_another_conversation_cannot_be_sent() -> None:
    service, conversations, conversation_id = await _setup()
    attachment = await service.upload(ALICE, conversation_id, "a.png", PNG)
    await conversations.set_title(conversation_id, "first")
    other = await conversations.get_or_create_empty(ALICE)

    with pytest.raises(AttachmentNotFoundError):
        await service.to_send(ALICE, other.id, [attachment.id])


async def test_only_an_unsent_attachment_can_be_discarded() -> None:
    service, conversations, conversation_id = await _setup()
    sent = await service.upload(ALICE, conversation_id, "a.png", PNG)
    unsent = await service.upload(ALICE, conversation_id, "b.png", PNG)
    await conversations.append_turn(
        conversation_id, "", [TextDelta(text="ok")], attachment_ids=[sent.id]
    )

    await service.discard(ALICE, conversation_id, unsent.id)

    with pytest.raises(AttachmentNotFoundError):
        await service.get(ALICE, conversation_id, unsent.id)
    with pytest.raises(AttachmentNotFoundError):
        await service.discard(ALICE, conversation_id, sent.id)
    assert (await service.get(ALICE, conversation_id, sent.id)).attachment == sent


async def test_prune_deletes_only_old_unsent_attachments() -> None:
    service, conversations, conversation_id = await _setup()
    sent = await service.upload(ALICE, conversation_id, "a.png", PNG)
    await service.upload(ALICE, conversation_id, "b.png", PNG)
    await conversations.append_turn(
        conversation_id, "", [TextDelta(text="ok")], attachment_ids=[sent.id]
    )

    # The fake's clock is in the past, so every upload is older than an hour.
    assert await service.prune(timedelta(hours=1)) == 1
    assert list(conversations.attachments) == [sent.id]
