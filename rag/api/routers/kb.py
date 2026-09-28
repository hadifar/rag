from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from rag.api.deps import RetrievalServiceDep
from rag.domain.errors import DocumentNotFoundError

router = APIRouter(prefix="/api/kb", tags=["kb"])


@router.get("/{filename}")
async def get_document(
    filename: str, retrieval_service: RetrievalServiceDep
) -> PlainTextResponse:
    document = await retrieval_service.get_document(filename)
    if document is None:
        raise DocumentNotFoundError(filename)
    return PlainTextResponse(document.page_content)
