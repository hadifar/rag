from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from rag.api.deps import RankingServiceDep
from rag.domain.errors import DocumentNotFoundError


def build_kb_router() -> APIRouter:
    router = APIRouter(tags=["kb"])

    @router.get("/{filename}")
    async def get_document(
        filename: str, ranking_service: RankingServiceDep
    ) -> PlainTextResponse:
        document = await ranking_service.get_document(filename)
        if document is None:
            raise DocumentNotFoundError(filename)
        return PlainTextResponse(document.page_content)

    return router
