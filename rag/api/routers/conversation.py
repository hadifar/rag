import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response

from rag.api.deps import (
    AttachmentServiceDep,
    AuthenticatedUserDep,
    ConversationServiceDep,
    ShareServiceDep,
    get_current_user,
)
from rag.api.schema.conversation import (
    DEFAULT_PAGE_LIMIT,
    AttachmentResponse,
    ConversationPageResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    HistoryMessageResponse,
    MessageRequest,
    PageLimit,
    to_history_message,
)
from rag.api.schema.share import ShareResponse
from rag.api.uploads import AttachmentUpload

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@router.post("")
async def create_conversation(
    current_user: AuthenticatedUserDep, conversation_service: ConversationServiceDep
) -> ConversationResponse:
    """The caller's empty conversation: a new one, or the one they already have."""
    conversation = await conversation_service.create(current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.get("")
async def list_conversations(
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
    limit: PageLimit = DEFAULT_PAGE_LIMIT,
    cursor: str | None = None,
) -> ConversationPageResponse:
    page = await conversation_service.list_for_user(current_user.id, limit, cursor)
    return ConversationPageResponse.model_validate(page)


@router.get("/pinned")
async def list_pinned_conversations(
    current_user: AuthenticatedUserDep, conversation_service: ConversationServiceDep
) -> list[ConversationResponse]:
    """The caller's pinned conversations, last pinned first; `GET ""` lists the rest."""
    conversations = await conversation_service.list_pinned(current_user.id)
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    conversation = await conversation_service.get_owned(
        current_user.id, conversation_id
    )
    return ConversationResponse.model_validate(conversation)


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: uuid.UUID,
    update_request: ConversationUpdateRequest,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    """Renames, or pins or unpins it."""
    conversation = await conversation_service.update(
        current_user.id, conversation_id, update_request.to_update()
    )
    return ConversationResponse.model_validate(conversation)


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> list[HistoryMessageResponse]:
    history = await conversation_service.history(current_user.id, conversation_id)
    return [to_history_message(m) for m in history]


@router.post("/{conversation_id}/title")
async def generate_title(
    conversation_id: uuid.UUID,
    message_request: MessageRequest,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    """Names the conversation from its first message (an LLM-written title, or one cut
    from the message if that fails); the client calls it as it sends that message,
    without waiting for the answer.
    """
    conversation = await conversation_service.generate_title(
        current_user.id, conversation_id, message_request.message
    )
    return ConversationResponse.model_validate(conversation)


@router.get("/{conversation_id}/share")
async def get_share(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    share_service: ShareServiceDep,
) -> ShareResponse | None:
    """Its public link, or null if it isn't shared."""
    share = await share_service.get(current_user.id, conversation_id)
    return ShareResponse.model_validate(share) if share is not None else None


@router.put("/{conversation_id}/share")
async def share_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    share_service: ShareServiceDep,
) -> ShareResponse:
    """Shares it as it is now, behind its link (made on first share, kept after)."""
    share = await share_service.share(current_user.id, conversation_id)
    return ShareResponse.model_validate(share)


@router.delete("/{conversation_id}/share", status_code=204)
async def unshare_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    share_service: ShareServiceDep,
) -> None:
    await share_service.unshare(current_user.id, conversation_id)


@router.post("/{conversation_id}/attachments", status_code=201)
async def upload_attachment(
    conversation_id: uuid.UUID,
    upload: AttachmentUpload,
    current_user: AuthenticatedUserDep,
    attachment_service: AttachmentServiceDep,
) -> AttachmentResponse:
    """Keeps a file (.md, .png or .jpg) in the conversation, to send with a message by
    its id (`attachment_ids` of `POST /api/chat/{conversation_id}`).
    """
    attachment = await attachment_service.upload(
        current_user.id, conversation_id, upload
    )
    return AttachmentResponse.model_validate(attachment)


@router.get(
    "/{conversation_id}/attachments/{attachment_id}",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def get_attachment(
    conversation_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    attachment_service: AttachmentServiceDep,
) -> Response:
    """The attachment's content, typed as what it was recognized as."""
    file = await attachment_service.get(current_user.id, conversation_id, attachment_id)
    return Response(
        content=file.data,
        media_type=file.attachment.media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(file.attachment.name)}",
            # An attachment never changes.
            "Cache-Control": "private, max-age=31536000, immutable",
        },
    )


@router.delete("/{conversation_id}/attachments/{attachment_id}", status_code=204)
async def discard_attachment(
    conversation_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    attachment_service: AttachmentServiceDep,
) -> None:
    """Deletes an attachment that was never sent; one already sent stays (404)."""
    await attachment_service.discard(current_user.id, conversation_id, attachment_id)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    conversation_service: ConversationServiceDep,
) -> None:
    await conversation_service.delete(current_user.id, conversation_id)
