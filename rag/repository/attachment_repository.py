import hashlib
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, LiteralString

from rag.domain.models import Attachment, AttachmentFile
from rag.repository.base_repository import BaseRepository

_COLUMNS = (
    "a.id, a.conversation_id, a.name, a.media_type, a.size, a.sha256, a.created_at"
)

# Sent: listed by one of its conversation's turns.
_SENT = (
    "EXISTS (SELECT 1 FROM conversation_turn_attachments ta "
    "WHERE ta.attachment_id = a.id)"
)


class AttachmentRepository(BaseRepository[Attachment]):
    row_type = Attachment

    async def create(
        self, conversation_id: uuid.UUID, name: str, media_type: str, data: bytes
    ) -> Attachment:
        attachment = await self._fetch_one(
            f"""
            INSERT INTO conversation_attachments AS a
                (conversation_id, name, media_type, sha256, data)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (conversation_id, name, media_type, hashlib.sha256(data).hexdigest(), data),
        )
        assert attachment is not None  # an INSERT ... RETURNING always returns it
        return attachment

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> AttachmentFile | None:
        files = await self._fetch_files(
            f"""
            SELECT {_COLUMNS}, a.data FROM conversation_attachments a
            JOIN conversations c ON c.id = a.conversation_id
            WHERE a.id = %s AND a.conversation_id = %s AND c.user_id = %s
            """,
            (attachment_id, conversation_id, user_id),
        )
        return files[0] if files else None

    async def list_in(
        self, conversation_id: uuid.UUID, attachment_ids: Sequence[uuid.UUID]
    ) -> list[AttachmentFile]:
        files = await self._fetch_files(
            f"""
            SELECT {_COLUMNS}, a.data FROM conversation_attachments a
            WHERE a.conversation_id = %s AND a.id = ANY(%s)
            """,
            (conversation_id, list(attachment_ids)),
        )
        by_id = {f.attachment.id: f for f in files}
        return [by_id[i] for i in attachment_ids if i in by_id]

    async def list_sent(self, conversation_id: uuid.UUID) -> list[AttachmentFile]:
        return await self._fetch_files(
            f"""
            SELECT {_COLUMNS}, a.data FROM conversation_attachments a
            WHERE a.conversation_id = %s AND {_SENT}
            ORDER BY a.created_at, a.id
            """,
            (conversation_id,),
        )

    async def delete_unsent(
        self, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> bool:
        deleted = await self._execute(
            f"""
            DELETE FROM conversation_attachments a
            WHERE a.id = %s AND a.conversation_id = %s AND NOT {_SENT}
            """,
            (attachment_id, conversation_id),
        )
        return deleted > 0

    async def delete_unsent_before(self, cutoff: datetime) -> int:
        return await self._execute(
            f"""
            DELETE FROM conversation_attachments a
            WHERE a.created_at < %s AND NOT {_SENT}
            """,
            (cutoff,),
        )

    async def _fetch_files(
        self, query: LiteralString, params: Any
    ) -> list[AttachmentFile]:
        """Rows of the attachment's columns followed by its `data`."""
        async with self._pool.connection() as conn:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
        return [
            AttachmentFile(attachment=Attachment(*row[:-1]), data=bytes(row[-1]))
            for row in rows
        ]
