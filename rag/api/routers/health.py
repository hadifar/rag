from fastapi import APIRouter

from rag.container import ContainerHandle


def build_health_router(handle: ContainerHandle) -> APIRouter:
    router = APIRouter()

    @router.get("/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    async def ready() -> dict[str, str]:
        # Deliberately exercises the real retrieval path (dense+sparse Pinecone query)
        # rather than a bare ping, so "ready" actually means "can serve".
        await handle.get().ranking_service.search("healthcheck", top_k=1)
        return {"status": "ok"}

    return router
