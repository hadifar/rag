from fastapi import APIRouter

from rag.api.deps import ContainerDep
from rag.api.schema import HealthResponse


def build_health_router() -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/live")
    async def live() -> HealthResponse:
        return HealthResponse(status="ok")

    @router.get("/ready")
    async def ready(container: ContainerDep) -> HealthResponse:
        # Deliberately exercises the real retrieval path (dense+sparse Pinecone query)
        # rather than a bare ping, so "ready" actually means "can serve".
        await container.ranking_service.search("healthcheck", top_k=1)
        return HealthResponse(status="ok")

    return router
