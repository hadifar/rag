from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from rag.config import Settings


def build_kb_router(settings: Settings) -> APIRouter:
    router = APIRouter()
    base_dir = settings.KNOWLEDGE_BASE_DIR.resolve()

    @router.get("/{filename}")
    async def get_document(filename: str) -> PlainTextResponse:
        # Resolve before checking containment — the only defense against `../` traversal
        # or absolute-path filenames escaping the knowledge base directory.
        path = (base_dir / filename).resolve()
        if not path.is_relative_to(base_dir) or not path.is_file():
            raise HTTPException(status_code=404, detail="Document not found")
        return PlainTextResponse(path.read_text())

    return router
