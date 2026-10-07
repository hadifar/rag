import base64
import binascii
import json
import uuid
from dataclasses import replace
from datetime import datetime

from rag.domain.errors import (
    ConversationNotFoundError,
    InvalidCursorError,
)
from rag.domain.models import (
    Conversation,
    ConversationPage,
    HistoryMessage,
    RunContext,
    history_of,
)
from rag.domain.ports import (
    ConversationRepositoryPort,
    LLMPort,
)
from rag.services.conversation_service.title import (
    TitleOutput,
    fallback_title,
    title_prompt,
)
from rag.shared.resilience import or_default


class ConversationService:
    """A user's conversations: each one's transcript (written by `chat_service`), and
    its title, written by the LLM (`llm`).
    """

    def __init__(
        self,
        repository: ConversationRepositoryPort,
        llm: LLMPort,
    ):
        self._repository = repository
        self._llm = llm

    async def create(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty conversation, new or the one they already have, so empty
        conversations can't pile up. Its first message names it (see `generate_title`).
        """
        return await self._repository.get_or_create_empty(user_id)

    async def generate_title(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, message: str
    ) -> Conversation:
        """Names the conversation from its first `message`, with an LLM-written title, or
        if the LLM fails, one cut from the message. Needs no answer, so the client asks
        as it sends the message, not after the reply. Titling it also ends its life as
        the user's empty draft (see `create`).
        """
        conversation = await self.get_owned(user_id, conversation_id)
        prompt = title_prompt(message)
        reply = await or_default(
            self._llm.generate_structured(
                prompt,
                TitleOutput,
                trace="title",
                ctx=RunContext(user_id=user_id, conversation_id=conversation_id),
            ),
            None,
        )
        title = reply.title if reply is not None else fallback_title(message)
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

    async def list_pinned(self, user_id: uuid.UUID) -> list[Conversation]:
        """The user's pinned conversations, last pinned first. Not paged: the user
        picks each one, so there are few.
        """
        return await self._repository.list_pinned(user_id)

    async def update(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        *,
        title: str | None = None,
        pinned: bool | None = None,
    ) -> Conversation:
        """Renames it, pins or unpins it; a field left None stays as is. Neither
        counts as using it, so it keeps its place among the recent ones.
        """
        conversation = await self._repository.update_owned(
            user_id, conversation_id, title, pinned
        )
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def history(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> list[HistoryMessage]:
        """Each question, then its answer's events, if it sent any."""
        await self.get_owned(user_id, conversation_id)
        return history_of(await self._repository.list_turns(conversation_id))

    async def delete(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        """Its turns, and the agent's memory of them, go with the row."""
        await self.get_owned(user_id, conversation_id)
        await self._repository.delete(conversation_id)

    async def get_owned(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._repository.get_owned(user_id, conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation


def _encode_cursor(conversation: Conversation) -> str:
    payload = json.dumps([conversation.updated_at.isoformat(), str(conversation.id)])
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        updated_at, conversation_id = json.loads(base64.urlsafe_b64decode(cursor))
        return datetime.fromisoformat(updated_at), uuid.UUID(conversation_id)
    except (binascii.Error, ValueError, TypeError, AttributeError) as exc:
        raise InvalidCursorError() from exc
