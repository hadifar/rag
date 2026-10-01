import base64
import binascii
import json
import uuid
from dataclasses import replace
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from rag.domain.errors import (
    BlankTitleError,
    ConversationNotFoundError,
    InvalidCursorError,
)
from rag.domain.models import Conversation, ConversationPage, HistoryMessage
from rag.domain.ports import AgentServicePort, ConversationRepositoryPort
from rag.shared.resilience import or_default

TITLE_PROMPT = (
    "Write a title for a support conversation that starts with the message below.\n\n"
    "USER:\n{message}"
)
# Only the start of the message is needed to title it; caps the title call's cost.
TITLE_MESSAGE_EXCERPT = 1000
MAX_TITLE_LENGTH = 80  # cap on an LLM-written title
FALLBACK_TITLE_LENGTH = (
    60  # the title cut from the message when the LLM can't write one
)


class TitleOutput(BaseModel):
    """The LLM's title, tidied on the way in: trimmed and capped in length, and a blank
    one is rejected (`BlankTitleError`), so a `TitleOutput` always holds a usable title.
    """

    title: str = Field(description="At most 6 words, no quotes and no trailing period.")

    @field_validator("title")
    @classmethod
    def _tidy(cls, title: str) -> str:
        title = title.strip()[:MAX_TITLE_LENGTH]
        if not title:
            raise BlankTitleError
        return title


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepositoryPort,
        agent_service: AgentServicePort,
    ):
        self._repository = repository
        self._agent_service = agent_service

    async def create(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty conversation, new or the one they already have, so empty
        conversations can't pile up. Its first message names it (see `generate_title`).
        """
        return await self._repository.get_or_create_empty(user_id)

    async def touch(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        """Marks the user's conversation as just used, so it sorts first in their list."""
        await self.get_owned(user_id, conversation_id)
        if await self._repository.touch(conversation_id) is None:
            raise ConversationNotFoundError(conversation_id)  # deleted meanwhile

    async def generate_title(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, message: str
    ) -> Conversation:
        """Names the conversation from its first `message`, with an LLM-written title, or
        if the LLM fails, one cut from the message. Needs no answer, so the client asks
        as it sends the message, not after the reply. Titling it also ends its life as
        the user's empty draft (see `create`).
        """
        conversation = await self.get_owned(user_id, conversation_id)
        prompt = TITLE_PROMPT.format(message=message[:TITLE_MESSAGE_EXCERPT])
        reply = await or_default(
            self._agent_service.generate_structured(prompt, TitleOutput), None
        )
        title = reply.title if reply is not None else _fallback_title(message)
        await self._repository.set_title(conversation_id, title)
        return replace(conversation, title=title)

    async def list_for_user(
        self, user_id: uuid.UUID, limit: int, cursor: str | None
    ) -> ConversationPage:
        before = _decode_cursor(cursor) if cursor is not None else None
        # One extra row tells whether another page exists without a COUNT query.
        rows = await self._repository.list_for_user(user_id, limit + 1, before)
        items = rows[:limit]
        next_cursor = _encode_cursor(items[-1]) if len(rows) > limit else None
        return ConversationPage(items=items, next_cursor=next_cursor)

    async def history(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> list[HistoryMessage]:
        await self.get_owned(user_id, conversation_id)
        return await self._repository.get_history(str(conversation_id))

    async def delete(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        await self.get_owned(user_id, conversation_id)
        # Messages first: if this fails, the row is still there to retry the delete,
        # rather than a row-less thread nobody can reach (or erase) anymore.
        await self._repository.delete_history(str(conversation_id))
        await self._repository.delete(conversation_id)

    async def prune_orphaned_threads(self, *, dry_run: bool = False) -> list[str]:
        """Deletes stored messages whose conversation no longer exists, and returns their
        thread ids. Deleting a conversation removes its messages first, so these only come
        from a delete that failed halfway or rows removed outside the app.
        """
        conversation_ids = {str(id_) for id_ in await self._repository.all_ids()}
        orphans = sorted(await self._repository.list_thread_ids() - conversation_ids)
        if not dry_run:
            for thread_id in orphans:
                await self._repository.delete_history(thread_id)
        return orphans

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._repository.get(conversation_id)
        # Same error for "missing" and "someone else's", so ids can't be probed.
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        return conversation


def _fallback_title(message: str) -> str:
    title = " ".join(message.split())
    if len(title) <= FALLBACK_TITLE_LENGTH:
        return title
    return title[: FALLBACK_TITLE_LENGTH - 1].rstrip() + "…"


def _encode_cursor(conversation: Conversation) -> str:
    payload = json.dumps([conversation.updated_at.isoformat(), str(conversation.id)])
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        updated_at, conversation_id = json.loads(base64.urlsafe_b64decode(cursor))
        return datetime.fromisoformat(updated_at), uuid.UUID(conversation_id)
    except (binascii.Error, ValueError, TypeError, AttributeError) as exc:
        raise InvalidCursorError() from exc
