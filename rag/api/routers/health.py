from fastapi import APIRouter

from rag.api.deps import RankingServiceDep
from rag.api.schema.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/live")
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready")
async def ready(ranking_service: RankingServiceDep) -> HealthResponse:
    # Deliberately exercises the real retrieval path (dense+sparse Pinecone query)
    # rather than a bare ping, so "ready" actually means "can serve".
    await ranking_service.search("healthcheck", top_k=1)
    return HealthResponse(status="ok")
