import uuid

from rag.domain.models import Share
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, conversation_id, title, turn_count, shared_at"


class ShareRepository(BaseRepository[Share]):
    row_type = Share

    async def save(self, conversation_id: uuid.UUID, title: str) -> Share | None:
        # HAVING without GROUP BY yields no row for a conversation without turns, so
        # nothing is inserted and None comes back. Sharing again keeps the link's id.
        return await self._fetch_one(
            f"""
            INSERT INTO conversation_shares (conversation_id, title, turn_count)
            SELECT %(conversation_id)s, %(title)s, count(*)
            FROM conversation_turns WHERE conversation_id = %(conversation_id)s
            HAVING count(*) > 0
            ON CONFLICT (conversation_id) DO UPDATE SET
                title = EXCLUDED.title,
                turn_count = EXCLUDED.turn_count,
                shared_at = now()
            RETURNING {_COLUMNS}
            """,
            {"conversation_id": conversation_id, "title": title},
        )

    async def get_for_conversation(self, conversation_id: uuid.UUID) -> Share | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM conversation_shares WHERE conversation_id = %s",
            (conversation_id,),
        )

    async def get(self, share_id: uuid.UUID) -> Share | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM conversation_shares WHERE id = %s", (share_id,)
        )

    async def delete_for_conversation(self, conversation_id: uuid.UUID) -> None:
        await self._execute(
            "DELETE FROM conversation_shares WHERE conversation_id = %s",
            (conversation_id,),
        )
