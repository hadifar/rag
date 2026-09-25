from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from rag.api.deps import ContainerDep
from rag.domain.errors import DocumentNotFoundError


def build_kb_router() -> APIRouter:
    router = APIRouter(tags=["kb"])

    @router.get("/{filename}")
    async def get_document(filename: str, container: ContainerDep) -> PlainTextResponse:
        document = await container.ranking_service.get_document(filename)
        if document is None:
            raise DocumentNotFoundError(filename)
        return PlainTextResponse(document.page_content)

    return router
