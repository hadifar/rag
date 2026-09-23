from fastapi import APIRouter, Request

from rag.api.deps import get_container


def build_health_router() -> APIRouter:
    router = APIRouter()

    @router.get("/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    async def ready(request: Request) -> dict[str, str]:
        # Deliberately exercises the real retrieval path (dense+sparse Pinecone query)
        # rather than a bare ping, so "ready" actually means "can serve".
        await get_container(request).ranking_service.search("healthcheck", top_k=1)
        return {"status": "ok"}

    return router
