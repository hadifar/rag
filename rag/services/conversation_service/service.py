import asyncio
import base64
import binascii
import json
import logging
import uuid
from dataclasses import replace
from datetime import datetime

from rag.domain.errors import ConversationNotFoundError, InvalidCursorError
from rag.domain.models import Conversation, ConversationPage, HistoryMessage
from rag.domain.ports import ConversationRepositoryPort, GenerationPort
from rag.domain.prompts import TITLE_PROMPT

logger = logging.getLogger(__name__)

FALLBACK_TITLE_LENGTH = 60
MAX_TITLE_LENGTH = 80
# Only the start of the message is needed to title it; caps the title call's cost.
TITLE_MESSAGE_EXCERPT = 1000
# The client waits on this for the sidebar title; don't hold it on a slow LLM.
TITLE_TIMEOUT_SECONDS = 10


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepositoryPort,
        generation_service: GenerationPort,
    ):
        self._repository = repository
        self._generation = generation_service

    async def create(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty conversation, new or the one they already have, so empty
        conversations can't pile up. Its first message names it (see `chat`).
        """
        return await self._repository.get_or_create_empty(user_id)

    async def begin_chat(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, message: str
    ) -> None:
        """Readies the conversation for a turn: marks it used, and if it is untitled
        (a first message) names it with a title cut from `message` (see
        `generate_title` for a better one). Call before streaming the answer.
        """
        conversation = await self._touch_owned(user_id, conversation_id)
        if conversation.title is None:
            # Titled before streaming, so an empty conversation is always untitled
            # and vice versa — even if the answer then fails.
            await self._repository.set_title(conversation_id, _fallback_title(message))

    async def generate_title(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, message: str
    ) -> Conversation:
        """Renames the conversation with an LLM-written title for its first `message`.
        Needs no answer, so the client asks as it sends the message, not after the reply.
        Keeps the current title if the LLM fails.
        """
        conversation = await self.get_owned(user_id, conversation_id)
        title = await self._llm_title(message)
        if title is None:
            return conversation
        await self._repository.set_title(conversation_id, title)
        return replace(conversation, title=title)

    async def _llm_title(self, message: str) -> str | None:
        """An LLM-written title, or None to keep the fallback. Never raises: a failed
        title must not fail the turn the user already got an answer for.
        """
        prompt = TITLE_PROMPT.format(message=message[:TITLE_MESSAGE_EXCERPT])
        try:
            async with asyncio.timeout(TITLE_TIMEOUT_SECONDS):
                raw = await self._generation.generate(prompt)
        except Exception:
            logger.warning(
                "Title generation failed; keeping the fallback", exc_info=True
            )
            return None
        return _clean_title(raw)

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


def _clean_title(raw: str) -> str | None:
    first_line = next(iter(raw.strip().splitlines()), "")
    title = first_line.strip().strip("\"'`").strip().rstrip(".")
    return title[:MAX_TITLE_LENGTH] or None


def _encode_cursor(conversation: Conversation) -> str:
    payload = json.dumps([conversation.updated_at.isoformat(), str(conversation.id)])
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        updated_at, conversation_id = json.loads(base64.urlsafe_b64decode(cursor))
        return datetime.fromisoformat(updated_at), uuid.UUID(conversation_id)
    except (binascii.Error, ValueError, TypeError, AttributeError) as exc:
        raise InvalidCursorError() from exc
