import uuid
from typing import Annotated

from fastapi import Depends, Request
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


def get_retrieval_service(container: ContainerDep) -> RetrievalService:
    return container.retrieval_service


def get_auth_service(container: ContainerDep) -> AuthService:
    return container.auth_service


def get_ingestion_service(container: ContainerDep) -> IngestionService:
    return container.ingestion_service


def get_conversation_service(container: ContainerDep) -> ConversationService:
    return container.conversation_service


def get_chat_service(container: ContainerDep) -> ChatService:
    return container.chat_service


def get_share_service(container: ContainerDep) -> ShareService:
    return container.share_service


def get_attachment_service(container: ContainerDep) -> AttachmentService:
    return container.attachment_service


def get_skill_service(container: ContainerDep) -> SkillService:
    return container.skill_service


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


ShareServiceDep = Annotated[ShareService, Depends(get_share_service)]


AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]


SkillServiceDep = Annotated[SkillService, Depends(get_skill_service)]


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
