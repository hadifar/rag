from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag.config import Settings
from rag.container import Container
from rag.services.auth_service.service import AuthenticatedIdentity, AuthService
from rag.services.conversation_service.service import ConversationService
from rag.services.ingestion_service.service import IngestionService
from rag.services.rag_service.service import RagService
from rag.services.retrieval_service.service import RetrievalService

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


def get_rag_service(container: ContainerDep) -> RagService:
    return container.rag_service


RagServiceDep = Annotated[RagService, Depends(get_rag_service)]


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    auth_service: AuthServiceDep,
) -> AuthenticatedIdentity:
    return await auth_service.authenticate_access_token(credentials.credentials)


AuthenticatedUserDep = Annotated[AuthenticatedIdentity, Depends(get_current_user)]


def get_current_admin(identity: AuthenticatedUserDep) -> AuthenticatedIdentity:
    return AuthService.require_admin(identity)


AdminUserDep = Annotated[AuthenticatedIdentity, Depends(get_current_admin)]
