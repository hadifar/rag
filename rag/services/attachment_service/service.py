import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import PureWindowsPath

from rag.domain.errors import (
    AttachmentNotFoundError,
    AttachmentTooLargeError,
    UnsupportedAttachmentError,
)
from rag.domain.models import Attachment, AttachmentFile, Upload
from rag.domain.ports import AttachmentRepositoryPort, ConversationRepositoryPort
from rag.services.attachment_service.kinds import KINDS, AttachmentKind
from rag.shared.text_normalizer import one_line

MAX_NAME_LENGTH = 255  # characters kept of an uploaded file's name
FALLBACK_NAME = "attachment"


class AttachmentService:
    """Files a user attaches to their messages: uploaded to the conversation first,
    then sent with a message by id. One that's never sent is discarded by the user, or
    pruned once old (`prune`).
    """

    def __init__(
        self,
        attachments: AttachmentRepositoryPort,
        conversations: ConversationRepositoryPort,
        *,
        max_bytes: int,
        kinds: Sequence[AttachmentKind] = KINDS,
    ):
        """No file over `max_bytes` is accepted, whatever its kind; each kind may cap
        it lower.
        """
        self._attachments = attachments
        self._conversations = conversations
        self._max_bytes = max_bytes
        self._kinds = kinds

    async def upload(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, upload: Upload
    ) -> Attachment:
        """Keeps the file in the conversation, recognized by its content; raises if
        it's too large, no kind that can be attached, or too large for its kind.
        """
        await self._conversations.get_owned(user_id, conversation_id)
        # First: a file read only up to the cap is cut short, and may no longer look
        # like its kind.
        if len(upload.data) > self._max_bytes:
            raise AttachmentTooLargeError(self._max_bytes)
        name, data = _base_name(upload.name), upload.data
        kind = next((k for k in self._kinds if k.accepts(name, data)), None)
        if kind is None or not data:
            raise UnsupportedAttachmentError(", ".join(k.label for k in self._kinds))
        if len(data) > kind.max_bytes:
            raise AttachmentTooLargeError(kind.max_bytes)
        return await self._attachments.create(
            conversation_id, name, kind.media_type, data
        )

    async def get(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> AttachmentFile:
        file = await self._attachments.get_owned(
            user_id, conversation_id, attachment_id
        )
        if file is None:
            raise AttachmentNotFoundError(attachment_id)
        return file

    async def to_send(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        attachment_ids: Sequence[uuid.UUID],
    ) -> list[AttachmentFile]:
        """The attachments to send with a message, in the order given; each must be in
        the conversation. One already sent may be sent again (retrying a failed turn).
        """
        if not attachment_ids:
            return []
        await self._conversations.get_owned(user_id, conversation_id)
        files = await self._attachments.list_in(conversation_id, attachment_ids)
        found = {f.attachment.id for f in files}
        if missing := next((i for i in attachment_ids if i not in found), None):
            raise AttachmentNotFoundError(missing)
        return files

    async def discard(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> None:
        """Deletes an attachment the user removed before sending it. One already sent
        stays with its turn.
        """
        await self._conversations.get_owned(user_id, conversation_id)
        if not await self._attachments.delete_unsent(conversation_id, attachment_id):
            raise AttachmentNotFoundError(attachment_id)

    async def prune(self, older_than: timedelta) -> int:
        """Deletes the attachments uploaded more than `older_than` ago and never sent;
        returns how many.
        """
        cutoff = datetime.now(UTC) - older_than
        return await self._attachments.delete_unsent_before(cutoff)


def _base_name(name: str) -> str:
    """The file's own name, without the directories a client may send (with either
    slash), normalized as typed text, on one line, and capped in length.
    """
    base = one_line(PureWindowsPath(name).name)
    base = base[:MAX_NAME_LENGTH]
    return base or FALLBACK_NAME
