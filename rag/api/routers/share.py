import uuid

from fastapi import APIRouter

from rag.api.deps import ShareServiceDep
from rag.api.schema.share import SharedConversationResponse, to_shared_conversation

# Public: a share link is read by anyone who has it, signed in or not. The owner's
# routes (share, unshare) are on the conversations router, behind sign-in.
router = APIRouter(prefix="/api/shares", tags=["shares"])


@router.get("/{share_id}")
async def get_shared_conversation(
    share_id: uuid.UUID, share_service: ShareServiceDep
) -> SharedConversationResponse:
    """A shared conversation as it was when shared; 404 once its link is taken down."""
    shared = await share_service.shared(share_id)
    return to_shared_conversation(shared)
