import asyncio
import uuid
from collections.abc import AsyncIterator

from rag.domain.errors import ConversationNotFoundError
from rag.domain.models import RunContext, StreamEvent
from rag.domain.ports import AgentPort, ConversationRepositoryPort
from rag.services.chat_service.transcript import TranscriptBuilder


class ChatService:
    """A chat turn: the user's message answered by the agent (`agent`),
    given its memory of the earlier turns, streamed back, and kept in the
    conversation's transcript as the user saw it, beside the agent's memory of it.
    """

    def __init__(
        self,
        repository: ConversationRepositoryPort,
        agent: AgentPort,
    ):
        self._repository = repository
        self._agent = agent

    async def send_message(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, message: str
    ) -> AsyncIterator[StreamEvent]:
        """The answer's events as the agent streams them. The conversation sorts
        first in the user's list from the start, not once answered. The turn is saved
        to the transcript however the stream ends, so a failed or abandoned answer
        still shows what the user saw of it.
        """
        conversation = await self._repository.get(conversation_id)
        # Same error for "missing" and "someone else's", so ids can't be probed.
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        await self._repository.touch(conversation_id)
        turns = await self._repository.list_turns(conversation_id)
        history = [turn.memory for turn in turns if turn.memory is not None]
        ctx = RunContext(user_id=user_id, conversation_id=conversation_id)
        answer = self._agent.stream(message, history, ctx)
        transcript = TranscriptBuilder()
        try:
            async for event in answer:
                transcript.add(event)
                yield event
        finally:
            # Shielded: a client hanging up cancels the stream, not the save.
            await asyncio.shield(
                self._repository.append_turn(
                    conversation_id, message, transcript.events, answer.memory
                )
            )
