from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

from rag.adapters.checkpointer import open_checkpointer
from rag.adapters.db import open_db_pool
from rag.adapters.llm_client import build_llm
from rag.adapters.observability import open_trace_config
from rag.adapters.pinecone_client import open_vector_store
from rag.config import Settings
from rag.repository.user_repository import PostgresUserRepository
from rag.services.auth_service.service import AuthService
from rag.services.generation_service.service import GenerationService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.service import RetrievalService


@dataclass
class Container:
    ranking_service: RetrievalService
    generation_service: GenerationService
    ingestion_service: IngestionService
    auth_service: AuthService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container]:
    """Opens connections and tears it down on exit."""

    async with (
        open_vector_store(settings) as vector_store,
        open_checkpointer(settings) as checkpointer,
        open_trace_config(settings) as trace_config,
        open_db_pool(settings) as db_pool,
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

        auth_service = AuthService(
            user_repository=PostgresUserRepository(db_pool),
            jwt_secret=settings.AUTH.JWT_SECRET.get_secret_value(),
            jwt_algorithm=settings.AUTH.JWT_ALGORITHM,
            access_ttl=timedelta(minutes=settings.AUTH.ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_ttl=timedelta(days=settings.AUTH.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        yield Container(
            ranking_service, generation_service, ingestion_service, auth_service
        )
