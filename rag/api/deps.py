from typing import Annotated

from fastapi import Depends, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag.api.schema.chat import ChatRequest
from rag.container import Container
from rag.domain.models import User
from rag.services.auth_service.service import AuthService
from rag.services.conversation_service.service import ConversationService, Turn
from rag.services.ingestion_service.service import (
    MAX_ARCHIVE_BYTES,
    IngestionService,
)
from rag.services.retrieval_service.service import RetrievalService

# A bearer token from POST /api/auth/login. Not OAuth2PasswordBearer: login takes JSON,
# not the OAuth2 password form that /docs' Authorize button would post.
_bearer = HTTPBearer()


def get_container(request: Request) -> Container:
    """FastAPI dependency: reads the Container the lifespan stashed on app.state."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Container not initialized — app lifespan hasn't started")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_retrieval_service(container: ContainerDep) -> RetrievalService:
    return container.retrieval_service


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]


def get_auth_service(container: ContainerDep) -> AuthService:
    return container.auth_service


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_ingestion_service(container: ContainerDep) -> IngestionService:
    return container.ingestion_service


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


def get_conversation_service(container: ContainerDep) -> ConversationService:
    return container.conversation_service


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    auth_service: AuthServiceDep,
) -> User:
    user_id = auth_service.verify_access_token(credentials.credentials)
    return await auth_service.get_user(user_id)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_current_admin(user: CurrentUserDep) -> User:
    return AuthService.require_admin(user)


AdminUserDep = Annotated[User, Depends(get_current_admin)]


async def start_turn(
    chat_request: ChatRequest,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> Turn:
    """A dependency, so it runs before a streaming response starts: an unknown or
    foreign conversation is a plain 404 rather than an error in an already-200 stream.
    """
    return await conversation_service.start_turn(
        current_user.id, chat_request.conversation_id, chat_request.message
    )


TurnDep = Annotated[Turn, Depends(start_turn)]


async def read_archive_upload(file: UploadFile) -> bytes:
    """One byte over the limit is enough for the service to reject the upload, without
    ever holding an oversized one in memory.
    """
    return await file.read(MAX_ARCHIVE_BYTES + 1)


ArchiveUploadDep = Annotated[bytes, Depends(read_archive_upload)]
