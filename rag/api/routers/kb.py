from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from rag.api.deps import get_container


def build_kb_router() -> APIRouter:
    router = APIRouter()

    @router.get("/{filename}")
    async def get_document(filename: str, request: Request) -> PlainTextResponse:
        document = await get_container(request).ranking_service.get_document(filename)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return PlainTextResponse(document.page_content)

    return router
