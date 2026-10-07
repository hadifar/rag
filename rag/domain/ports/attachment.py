import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from rag.domain.models import Attachment, AttachmentFile


class AttachmentRepositoryPort(Protocol):
    """The files users attach to their conversations' messages. Which turns each one
    was sent with is the conversation repository's to record (`append_turn`).
    """

    async def create(
        self, conversation_id: uuid.UUID, name: str, media_type: str, data: bytes
    ) -> Attachment: ...

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> AttachmentFile | None:
        """None if it isn't in that conversation of the user's."""
        ...

    async def list_in(
        self, conversation_id: uuid.UUID, attachment_ids: Sequence[uuid.UUID]
    ) -> list[AttachmentFile]:
        """Those of `attachment_ids` in the conversation, in the order given; one
        that isn't is left out.
        """
        ...

    async def list_sent(self, conversation_id: uuid.UUID) -> list[AttachmentFile]:
        """Every attachment sent with one of the conversation's turns."""
        ...

    async def delete_unsent(
        self, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> bool:
        """Deletes it if it's in the conversation and was never sent; whether it was."""
        ...

    async def delete_unsent_before(self, cutoff: datetime) -> int:
        """Deletes every attachment uploaded before `cutoff` and never sent; returns
        how many.
        """
        ...
