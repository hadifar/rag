from fastapi import APIRouter

from rag.api.deps import RetrievalServiceDep
from rag.api.schema.health import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/live")
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready")
async def ready(retrieval_service: RetrievalServiceDep) -> HealthResponse:
    await retrieval_service.ping()
    return HealthResponse(status="ok")
