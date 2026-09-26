from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from rag.config import Settings, get_settings
from rag.container import Container
from rag.domain.models import User
from rag.services.auth_service.service import AuthService
from rag.services.generation_service.service import GenerationService
from rag.services.retrieval_service.service import RetrievalService

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_container(request: Request) -> Container:
    """FastAPI dependency: reads the Container the lifespan stashed on app.state."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Container not initialized — app lifespan hasn't started")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_ranking_service(container: ContainerDep) -> RetrievalService:
    return container.ranking_service


def get_generation_service(container: ContainerDep) -> GenerationService:
    return container.generation_service


RankingServiceDep = Annotated[RetrievalService, Depends(get_ranking_service)]

GenerationServiceDep = Annotated[GenerationService, Depends(get_generation_service)]


def get_auth_service(container: ContainerDep) -> AuthService:
    return container.auth_service


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)], auth_service: AuthServiceDep
) -> User:
    user_id = auth_service.verify_access_token(token)
    return await auth_service.get_user(user_id)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
