from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from rag.api.deps import get_current_user
from rag.api.error_handlers import register_error_handlers
from rag.api.routers.auth import router as auth_router
from rag.api.routers.chat import router as chat_router
from rag.api.routers.health import router as health_router
from rag.api.routers.kb import router as kb_router
from rag.api.routers.settings import router as settings_router
from rag.config import Settings, get_settings
from rag.container import Container, build_container


def _build_lifespan(container: Container | None, settings: Settings):
    # mirroring the FastAPI lifespan pattern from https://www.pinecone.io/learn/pinecone-async-fastapi/.
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        app.state.settings = settings

        if container is not None:
            app.state.container = container
            yield
            return

        async with build_container(settings) as built:
            app.state.container = built
            yield

    return lifespan


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    require_user = [Depends(get_current_user)]

    app = FastAPI(title="RAG", lifespan=_build_lifespan(container, settings))

    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(chat_router, dependencies=require_user)
    app.include_router(kb_router, dependencies=require_user)
    app.include_router(settings_router, dependencies=require_user)

    register_error_handlers(app)

    return app
