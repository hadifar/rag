from typing import Annotated

from fastapi import Depends, Request

from rag.container import Container
from rag.services.generation_service.service import GenerationService
from rag.services.retrieval_service.service import RetrievalService


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
