from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag.adapters.observability import flush
from rag.api.routers.chat import build_chat_router
from rag.api.routers.health import build_health_router
from rag.api.routers.kb import build_kb_router
from rag.api.routers.settings import build_settings_router
from rag.config import Settings, get_settings
from rag.container import Container, ContainerHandle, build_container


def _build_lifespan(handle: ContainerHandle, settings: Settings):
    # A pre-built container (tests) owns its own lifecycle; otherwise open one for
    # the app's lifetime, mirroring the FastAPI lifespan pattern from
    # https://www.pinecone.io/learn/pinecone-async-fastapi/.
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        if handle.container is not None:
            yield
            return

        async with build_container(settings) as built:
            handle.container = built
            yield
            handle.container = None
        flush()

    return lifespan


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    handle = ContainerHandle(container)

    app = FastAPI(title="RAG", lifespan=_build_lifespan(handle, settings))
    app.include_router(build_chat_router(handle), prefix="/api/chat")
    app.include_router(build_health_router(handle), prefix="/api/health")
    app.include_router(build_kb_router(settings), prefix="/api/kb")
    app.include_router(build_settings_router(settings), prefix="/api/settings")
    return app
