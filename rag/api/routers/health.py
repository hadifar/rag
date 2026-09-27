from fastapi import APIRouter

from rag.api.deps import RankingServiceDep
from rag.api.schema.health import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/live")
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready")
async def ready(ranking_service: RankingServiceDep) -> HealthResponse:
    await ranking_service.ping()
    return HealthResponse(status="ok")
