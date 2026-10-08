import uuid

from rag.domain.errors import NothingToShareError, ShareNotFoundError
from rag.domain.models import Share, SharedConversation, history_of
from rag.domain.ports import ConversationRepositoryPort, ShareRepositoryPort


class ShareService:
    """Public read-only links to conversations. A link shows its conversation as it was
    when shared (a snapshot of its title and turns); sharing again updates what the same
    link shows. Deleting the conversation takes its link down.
    """

    def __init__(
        self,
        shares: ShareRepositoryPort,
        conversations: ConversationRepositoryPort,
    ):
        self._shares = shares
        self._conversations = conversations

    async def share(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> Share:
        """Shares the user's conversation as it is now; one without messages can't be."""
        conversation = await self._conversations.get_owned(user_id, conversation_id)
        # Untitled means empty: its first message names it.
        share = (
            await self._shares.save(conversation_id, conversation.title)
            if conversation.title is not None
            else None
        )
        if share is None:
            raise NothingToShareError(conversation_id)
        return share

    async def get(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> Share | None:
        """The link to the user's conversation, or None if it isn't shared."""
        await self._conversations.get_owned(user_id, conversation_id)
        return await self._shares.get_for_conversation(conversation_id)

    async def unshare(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        """Takes its link down; already unshared is fine."""
        await self._conversations.get_owned(user_id, conversation_id)
        await self._shares.delete_for_conversation(conversation_id)

    async def shared(self, share_id: uuid.UUID) -> SharedConversation:
        """What anyone with the link sees, signed in or not."""
        share = await self._shares.get(share_id)
        if share is None:
            raise ShareNotFoundError(share_id)
        turns = await self._conversations.list_turns(
            share.conversation_id, share.turn_count
        )
        return SharedConversation(share=share, history=history_of(turns))
