import asyncio
import uuid
from collections.abc import AsyncIterator, Sequence

from rag.domain.errors import UserNotFoundError
from rag.domain.models import AttachmentFile, RunContext, StreamEvent
from rag.domain.ports import (
    AgentPort,
    AttachmentRepositoryPort,
    ConversationRepositoryPort,
    UserRepositoryPort,
)
from rag.services.chat_service.transcript import TranscriptBuilder


class ChatService:
    """A chat turn: the user's message and its attachments answered by the agent
    (`agent`), given its memory of the earlier turns and their attachments, streamed
    back, and kept in the conversation's transcript as the user saw it, beside the
    agent's memory of it.
    """

    def __init__(
        self,
        repository: ConversationRepositoryPort,
        attachments: AttachmentRepositoryPort,
        users: UserRepositoryPort,
        agent: AgentPort,
    ):
        self._repository = repository
        self._users = users
        self._attachments = attachments
        self._agent = agent

    async def send_message(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message: str,
        attachments: Sequence[AttachmentFile] = (),
    ) -> AsyncIterator[StreamEvent]:
        """The answer's events as the agent streams them. `attachments` are the
        conversation's own (see `AttachmentService.to_send`). The conversation sorts
        first in the user's list from the start, not once answered. The turn is saved
        to the transcript however the stream ends, so a failed or abandoned answer
        still shows what the user saw of it.
        """
        await self._repository.touch_owned(user_id, conversation_id)
        turns = await self._repository.list_turns(conversation_id)
        history = [turn.memory for turn in turns if turn.memory is not None]
        earlier_attachments = await self._attachments.list_sent(conversation_id)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        ctx = RunContext(
            user_id=user_id,
            conversation_id=conversation_id,
            model=user.model,
            effort=user.effort,
        )
        answer = self._agent.stream(
            message,
            history,
            ctx,
            attachments=attachments,
            earlier_attachments=earlier_attachments,
        )
        transcript = TranscriptBuilder()
        try:
            async for event in answer:
                transcript.add(event)
                yield event
        finally:
            # Shielded: a client hanging up cancels the stream, not the save.
            await asyncio.shield(
                self._repository.append_turn(
                    conversation_id,
                    message,
                    transcript.events,
                    answer.memory,
                    [f.attachment.id for f in attachments],
                )
            )
