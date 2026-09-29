from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from rag.api.deps import RetrievalServiceDep, get_current_user
from rag.domain.errors import DocumentNotFoundError

router = APIRouter(
    prefix="/api/kb", tags=["kb"], dependencies=[Depends(get_current_user)]
)


@router.get("/{filename}")
async def get_document(
    filename: str, retrieval_service: RetrievalServiceDep
) -> PlainTextResponse:
    document = await retrieval_service.get_document(filename)
    if document is None:
        raise DocumentNotFoundError(filename)
    return PlainTextResponse(document.page_content)
