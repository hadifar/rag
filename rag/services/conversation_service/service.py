import base64
import binascii
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import datetime

from rag.domain.errors import ConversationNotFoundError, InvalidCursorError
from rag.domain.events import StreamEvent
from rag.domain.models import Conversation, ConversationPage, HistoryMessage
from rag.domain.ports import ConversationRepositoryPort, GenerationPort

FALLBACK_TITLE_LENGTH = 60


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepositoryPort,
        generation: GenerationPort,
    ):
        self._repository = repository
        self._generation = generation

    async def create(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty conversation, new or the one they already have, so empty
        conversations can't pile up. Its first message names it (see `chat`).
        """
        return await self._repository.get_or_create_empty(user_id)

    async def chat(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, message: str
    ) -> AsyncIterator[StreamEvent]:
        """Streams the answer to `message`. A first message also names the conversation,
        with a title cut from the message (see `generate_title` for a better one).
        """
        conversation = await self._touch_owned(user_id, conversation_id)
        if conversation.title is None:
            # Titled before streaming, so an empty conversation is always untitled
            # and vice versa — even if the answer then fails.
            await self._repository.set_title(conversation_id, _fallback_title(message))
        async for event in self._generation.stream_chat(message, str(conversation_id)):
            yield event

    async def generate_title(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        """Renames the conversation with an LLM-written title for its first exchange.
        Keeps the current title if there's no answered exchange yet or the LLM fails.
        """
        conversation = await self.get_owned(user_id, conversation_id)
        match await self._generation.get_history(str(conversation_id)):
            case [
                HistoryMessage(role="user", text=question),
                HistoryMessage(role="assistant", text=answer),
                *_,
            ]:
                title = await self._generation.generate_title(question, answer)
            case _:
                title = None
        if title is None:
            return conversation
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
        return await self._generation.get_history(str(conversation_id))

    async def delete(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        await self.get_owned(user_id, conversation_id)
        # Messages first: if this fails, the row is still there to retry the delete,
        # rather than a row-less thread nobody can reach (or erase) anymore.
        await self._generation.delete_history(str(conversation_id))
        await self._repository.delete(conversation_id)

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._repository.get(conversation_id)
        # Same error for "missing" and "someone else's", so ids can't be probed.
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def _touch_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        """The user's conversation, marked as just used."""
        conversation = await self.get_owned(user_id, conversation_id)
        if await self._repository.touch(conversation_id) is None:
            raise ConversationNotFoundError(conversation_id)  # deleted meanwhile
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
