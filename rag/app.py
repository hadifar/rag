import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag.api.error_handlers import register_error_handlers
from rag.api.routers.auth import router as auth_router
from rag.api.routers.conversations import router as conversations_router
from rag.api.routers.health import router as health_router
from rag.api.routers.ingestions import router as ingestions_router
from rag.api.routers.kb import router as kb_router
from rag.api.routers.settings import router as settings_router
from rag.config import Settings, get_settings
from rag.container import Container, build_container

logger = logging.getLogger(__name__)


def _build_lifespan(container: Container | None, settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        if container is not None:
            app.state.container = container
            yield
            return

        async with build_container(settings) as built:
            await _fail_interrupted_runs(built)
            app.state.container = built
            yield

    return lifespan


async def _fail_interrupted_runs(container: Container) -> None:
    try:
        count = await container.ingestion_service.fail_interrupted_runs()
    except Exception:
        # E.g. migrations not applied yet — that mustn't stop the app from serving.
        logger.warning("Couldn't check for interrupted ingestion runs", exc_info=True)
        return
    if count:
        logger.warning("Marked %d interrupted ingestion run(s) as failed", count)


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="RAG", lifespan=_build_lifespan(container, settings))

    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(conversations_router)
    app.include_router(kb_router)
    app.include_router(ingestions_router)
    app.include_router(settings_router)

    register_error_handlers(app)

    return app
