import gradio as gr
from fastapi import FastAPI

from rag.api.routers.chat import build_chat_router
from rag.api.routers.health import build_health_router
from rag.api.routers.kb import build_kb_router
from rag.config import Settings, get_settings
from rag.container import Container, build_container
from rag.ui.gradio_app import build_gradio_ui


def create_app(
    container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    container = container or build_container(settings)

    app = FastAPI(title="RAG")
    app.include_router(build_chat_router(container.generation_service), prefix="/chat")
    app.include_router(build_health_router(container.ranking_service), prefix="/health")
    app.include_router(build_kb_router(settings), prefix="/kb")

    demo = build_gradio_ui(container.generation_service)
    gr.mount_gradio_app(app, demo, path="/ui")
    return app
