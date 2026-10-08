import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rag.api.routers.auth import router as auth_router
from rag.api.routers.chat import router as chat_router
from rag.api.routers.conversation import router as conversation_router
from rag.api.routers.health import router as health_router
from rag.api.routers.ingestion import router as ingestion_router
from rag.api.routers.retrieval import router as retrieval_router
from rag.api.routers.setting import router as setting_router
from rag.api.routers.share import router as share_router
from rag.api.routers.skill import router as skill_router
from rag.config import Settings, get_settings
from rag.container import Container, build_container, instrument_app
from rag.domain.errors import AppError

logger = logging.getLogger(__name__)


def _build_lifespan(container: Container | None, settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        if container is not None:
            app.state.container = container
            yield
            return

        async with build_container(settings) as built:
            app.state.container = built
            yield

    return lifespan


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    # Logged here because uvicorn's own log of it never reaches the root logger, so
    # telemetry would see it only on a sampled request trace. Same body shape as AppError.
    @app.exception_handler(Exception)
    async def _handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unexpected error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="RAG", lifespan=_build_lifespan(container, settings))

    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(conversation_router)
    app.include_router(chat_router)
    app.include_router(retrieval_router)
    app.include_router(ingestion_router)
    app.include_router(setting_router)
    app.include_router(share_router)
    app.include_router(skill_router)

    register_error_handlers(app)
    instrument_app(app, settings)

    return app
