import asyncio
import base64
import binascii
import json
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from langchain_core.runnables import Runnable

from rag.domain.errors import ConversationNotFoundError, InvalidCursorError
from rag.domain.events import (
    ConversationReady,
    ConversationTitled,
    StreamEvent,
    TextDelta,
)
from rag.domain.models import Conversation, ConversationPage, HistoryMessage
from rag.domain.ports import ChatEnginePort, ConversationRepositoryPort

logger = logging.getLogger(__name__)

TITLE_PROMPT = (
    "Write a title of at most 6 words for a support conversation that starts with the "
    "exchange below. Reply with the title only, without quotes or a trailing period.\n\n"
    "USER:\n{question}\n\nASSISTANT:\n{answer}"
)

FALLBACK_TITLE_LENGTH = 60
MAX_TITLE_LENGTH = 80
# Only the start of the answer is needed to title it; caps the title call's cost.
TITLE_ANSWER_EXCERPT = 1000
# The stream stays open until the title arrives; don't hold it on a slow LLM.
TITLE_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Turn:
    conversation: Conversation
    is_new: bool


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepositoryPort,
        chat_engine: ChatEnginePort,
        title_model: Runnable,
    ):
        self._repository = repository
        self._chat_engine = chat_engine
        self._title_model = title_model

    async def start_turn(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID | None, message: str
    ) -> Turn:
        """Resolves the conversation a message belongs to before any streaming starts,
        so someone else's id fails as a plain 404 instead of mid-stream.

        An id not seen before (the client generates it for a new chat) or no id starts
        a new conversation, owned by `user_id` and titled after the message until
        `stream_turn` generates a real title.
        """
        existing = (
            await self._repository.get(conversation_id) if conversation_id else None
        )
        if existing is None:
            conversation = await self._repository.create(
                user_id, _fallback_title(message), conversation_id
            )
            return Turn(conversation, is_new=True)

        if existing.user_id != user_id:
            raise ConversationNotFoundError(existing.id)
        conversation = await self._repository.touch(existing.id)
        if conversation is None:  # deleted between the ownership check and now
            raise ConversationNotFoundError(existing.id)
        return Turn(conversation, is_new=False)

    async def stream_turn(self, turn: Turn, message: str) -> AsyncIterator[StreamEvent]:
        conversation = turn.conversation
        yield ConversationReady(conversation=conversation)

        answer: list[str] = []
        async for event in self._chat_engine.stream_chat(message, str(conversation.id)):
            if isinstance(event, TextDelta):
                answer.append(event.text)
            yield event

        if turn.is_new:
            title = await self._generate_title(message, "".join(answer))
            if title is not None:
                await self._repository.set_title(conversation.id, title)
                yield ConversationTitled(
                    conversation_id=str(conversation.id), title=title
                )

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
        await self._get_owned(user_id, conversation_id)
        return await self._chat_engine.get_history(str(conversation_id))

    async def delete(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        await self._get_owned(user_id, conversation_id)
        # Messages first: if this fails, the row is still there to retry the delete,
        # rather than a row-less thread nobody can reach (or erase) anymore.
        await self._chat_engine.delete_history(str(conversation_id))
        await self._repository.delete(conversation_id)

    async def _get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._repository.get(conversation_id)
        # Same error for "missing" and "someone else's", so ids can't be probed.
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def _generate_title(self, question: str, answer: str) -> str | None:
        """An LLM-written title, or None to keep the fallback. Never raises: a failed
        title must not fail the turn the user already got an answer for.
        """
        prompt = TITLE_PROMPT.format(
            question=question, answer=answer[:TITLE_ANSWER_EXCERPT]
        )
        try:
            async with asyncio.timeout(TITLE_TIMEOUT_SECONDS):
                reply = await self._title_model.ainvoke(prompt)
        except Exception:
            logger.warning(
                "Title generation failed; keeping the fallback", exc_info=True
            )
            return None
        return _clean_title(str(reply.content))


def _fallback_title(message: str) -> str:
    title = " ".join(message.split())
    if len(title) <= FALLBACK_TITLE_LENGTH:
        return title
    return title[: FALLBACK_TITLE_LENGTH - 1].rstrip() + "…"


def _clean_title(raw: str) -> str | None:
    first_line = raw.strip().splitlines()[0] if raw.strip() else ""
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
