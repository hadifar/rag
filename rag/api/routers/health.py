from fastapi import APIRouter

from rag.services.ranking_service.service import RankingService


def build_health_router(ranking_service: RankingService) -> APIRouter:
    router = APIRouter()

    @router.get("/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    async def ready() -> dict[str, str]:
        # Deliberately exercises the real retrieval path (embed + Pinecone query) rather
        # than a bare ping, so "ready" actually means "can serve" — costs one small
        # embedding call per probe hit, acceptable for a readiness check.
        await ranking_service.search("healthcheck", top_k=1)
        return {"status": "ok"}

    return router
