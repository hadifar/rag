from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from rag.api.deps import get_current_user
from rag.api.routers.auth import router as auth_router
from rag.api.routers.chat import router as chat_router
from rag.api.routers.health import router as health_router
from rag.api.routers.kb import router as kb_router
from rag.api.routers.settings import router as settings_router
from rag.config import Settings, get_settings
from rag.container import Container, build_container
from rag.domain.errors import (
    DocumentNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    RagError,
    UserNotFoundError,
)


def _build_lifespan(container: Container | None, settings: Settings):
    # mirroring the FastAPI lifespan pattern from https://www.pinecone.io/learn/pinecone-async-fastapi/.
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        if container is not None:
            app.state.container = container
            yield
            return

        async with build_container(settings) as built:
            app.state.container = built
            yield

    return lifespan


def _register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(DocumentNotFoundError)
    async def _handle_not_found(
        request: Request, exc: DocumentNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidCredentialsError)
    @app.exception_handler(InvalidTokenError)
    @app.exception_handler(UserNotFoundError)
    async def _handle_unauthorized(request: Request, exc: RagError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(RagError)
    async def _handle_rag_error(request: Request, exc: RagError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    require_user = [Depends(get_current_user)]

    app = FastAPI(title="RAG", lifespan=_build_lifespan(container, settings))
    # Routers pull config via Depends(get_settings) — override so a caller-supplied
    # `settings` (e.g. a test's stub) is what every route actually sees, not the
    # real @lru_cache'd one get_settings() would otherwise return.
    app.dependency_overrides[get_settings] = lambda: settings

    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(chat_router, prefix="/api/chat", dependencies=require_user)
    app.include_router(health_router, prefix="/api/health")
    app.include_router(kb_router, prefix="/api/kb", dependencies=require_user)
    app.include_router(
        settings_router, prefix="/api/settings", dependencies=require_user
    )
    _register_error_handlers(app)
    return app
