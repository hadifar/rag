import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag.api.schema.conversation import ChatMessageRequest
from rag.config import Settings
from rag.container import Container
from rag.domain.models import AttachmentFile
from rag.services.attachment_service.service import AttachmentService
from rag.services.auth_service.service import AuthenticatedIdentity, AuthService
from rag.services.chat_service.service import ChatService
from rag.services.conversation_service.service import ConversationService
from rag.services.share_service.service import ShareService
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.service import RetrievalService
from rag.services.skill_service.service import SkillService

# A bearer token from POST /api/auth/login. Not OAuth2PasswordBearer: login takes JSON,
# not the OAuth2 password form that /docs' Authorize button would post.
_bearer = HTTPBearer()


def get_container(request: Request) -> Container:
    """The Container the lifespan stashed on app.state."""
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_app_settings(request: Request) -> Settings:
    """The Settings create_app stashed on app.state."""
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def _from_container[T](service: Callable[[Container], T]) -> Any:
    """A dependency on the Container's `service`."""

    def get(container: ContainerDep) -> T:
        return service(container)

    return Depends(get)


RetrievalServiceDep = Annotated[
    RetrievalService, _from_container(lambda c: c.retrieval_service)
]
IngestionServiceDep = Annotated[
    IngestionService, _from_container(lambda c: c.ingestion_service)
]
AuthServiceDep = Annotated[AuthService, _from_container(lambda c: c.auth_service)]
ConversationServiceDep = Annotated[
    ConversationService, _from_container(lambda c: c.conversation_service)
]
ChatServiceDep = Annotated[ChatService, _from_container(lambda c: c.chat_service)]
ShareServiceDep = Annotated[ShareService, _from_container(lambda c: c.share_service)]
AttachmentServiceDep = Annotated[
    AttachmentService, _from_container(lambda c: c.attachment_service)
]
SkillServiceDep = Annotated[SkillService, _from_container(lambda c: c.skill_service)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    auth_service: AuthServiceDep,
) -> AuthenticatedIdentity:
    return await auth_service.authenticate_access_token(credentials.credentials)


AuthenticatedUserDep = Annotated[AuthenticatedIdentity, Depends(get_current_user)]


def get_current_admin(identity: AuthenticatedUserDep) -> AuthenticatedIdentity:
    return AuthService.require_admin(identity)


AdminUserDep = Annotated[AuthenticatedIdentity, Depends(get_current_admin)]


async def get_attachments_to_send(
    conversation_id: uuid.UUID,
    message_request: ChatMessageRequest,
    current_user: AuthenticatedUserDep,
    attachment_service: AttachmentServiceDep,
) -> list[AttachmentFile]:
    """The chat message's attachments, looked up before its stream starts, so an
    unknown one is a plain 404 rather than an error in an already-200 stream.
    """
    return await attachment_service.to_send(
        current_user.id, conversation_id, message_request.attachment_ids
    )


AttachmentsToSendDep = Annotated[list[AttachmentFile], Depends(get_attachments_to_send)]


@dataclass(frozen=True)
class Upload:
    name: str  # as the client sent it, or "" if it sent none
    data: bytes


async def _read_capped(file: UploadFile, max_bytes: int) -> Upload:
    """The upload, read up to one byte past `max_bytes`: enough for the service to
    reject it, without ever holding an oversized one in memory.
    """
    return Upload(file.filename or "", await file.read(max_bytes + 1))


async def get_archive_upload(
    file: UploadFile, ingestion_service: IngestionServiceDep
) -> Upload:
    return await _read_capped(file, ingestion_service.max_archive_bytes)


async def get_skill_upload(file: UploadFile, skill_service: SkillServiceDep) -> Upload:
    return await _read_capped(file, skill_service.max_bytes)


async def get_attachment_upload(
    file: UploadFile, attachment_service: AttachmentServiceDep
) -> Upload:
    return await _read_capped(file, attachment_service.max_bytes)


ArchiveUploadDep = Annotated[Upload, Depends(get_archive_upload)]
SkillUploadDep = Annotated[Upload, Depends(get_skill_upload)]
AttachmentUploadDep = Annotated[Upload, Depends(get_attachment_upload)]
