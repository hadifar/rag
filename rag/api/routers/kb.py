from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from rag.container import ContainerHandle


def build_kb_router(handle: ContainerHandle) -> APIRouter:
    router = APIRouter()

    @router.get("/{filename}")
    async def get_document(filename: str) -> PlainTextResponse:
        document = await handle.get().ranking_service.get_document(filename)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return PlainTextResponse(document.page_content)

    return router
