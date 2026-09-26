from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rag.domain.errors import RagError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RagError)
    async def _handle_rag_error(request: Request, exc: RagError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})
