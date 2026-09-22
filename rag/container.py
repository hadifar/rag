from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from rag.adapters.checkpointer import open_checkpointer
from rag.adapters.llm_client import build_llm
from rag.adapters.observability import trace_config
from rag.adapters.pinecone_client import open_vector_store
from rag.config import Settings
from rag.services.generation_service.service import GenerationService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.service import RetrievalService


@dataclass
class Container:
    ranking_service: RetrievalService
    generation_service: GenerationService
    ingestion_service: IngestionService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container]:
    """Opens the vector store connection for the caller's scope and tears it down on
    exit — see rag.adapters.pinecone_client.open_vector_store.
    """
    async with (
        open_vector_store(settings) as vector_store,
        open_checkpointer(settings) as checkpointer,
    ):
        ranking_service = RetrievalService(vector_store=vector_store)

        generation_service = GenerationService(
            llm=build_llm(settings),
            ranking_service=ranking_service,
            checkpointer=checkpointer,
            trace_config=trace_config,
        )

        ingestion_service = IngestionService(
            vector_store=vector_store, chunker=WholeDocumentChunker()
        )

        yield Container(ranking_service, generation_service, ingestion_service)


class ContainerHandle:
    """Holds the active Container; the FastAPI lifespan swaps it in on startup.

    Routers and the Gradio UI are built once, before the lifespan runs (Gradio's
    mount_gradio_app and APIRouter both need their handlers up front), so they close
    over this handle and resolve `.get()` per-request rather than holding a Container
    directly.
    """

    def __init__(self, container: Container | None = None) -> None:
        self.container = container

    def get(self) -> Container:
        if self.container is None:
            raise RuntimeError(
                "Container not initialized — app lifespan hasn't started"
            )
        return self.container
