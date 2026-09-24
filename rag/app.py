from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag.api.routers.chat import build_chat_router
from rag.api.routers.health import build_health_router
from rag.api.routers.kb import build_kb_router
from rag.api.routers.settings import build_settings_router
from rag.config import Settings, get_settings
from rag.container import Container, build_container


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


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="RAG", lifespan=_build_lifespan(container, settings))
    app.include_router(build_chat_router(), prefix="/api/chat")
    app.include_router(build_health_router(), prefix="/api/health")
    app.include_router(build_kb_router(), prefix="/api/kb")
    app.include_router(build_settings_router(settings), prefix="/api/settings")
    return app
