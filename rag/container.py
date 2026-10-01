from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

from rag.adapters.archive_store import open_archive_store
from rag.adapters.argon2 import Argon2PasswordHasher
from rag.adapters.checkpointer import open_checkpointer
from rag.adapters.db import open_db_pool
from rag.adapters.history_store import CheckpointHistoryStore
from rag.adapters.jwt_codec import JwtTokenCodec
from rag.adapters.llm_client import build_embeddings, build_llm
from rag.adapters.observability import open_trace_config
from rag.config import Settings
from rag.repository.conversation_repository import ConversationRepository
from rag.repository.document_repository import DocumentRepository
from rag.repository.ingestion_run_repository import IngestionRunRepository
from rag.repository.user_repository import UserRepository
from rag.services.agent_service.service import AgentService
from rag.services.auth_service.service import AuthService
from rag.services.conversation_service.service import ConversationService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.rag_service.service import RagService
from rag.services.retrieval_service.service import RetrievalService


@dataclass
class Container:
    retrieval_service: RetrievalService
    agent_service: AgentService
    rag_service: RagService
    ingestion_service: IngestionService
    auth_service: AuthService
    conversation_service: ConversationService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container]:
    """Opens connections and tears it down on exit."""

    async with (
        open_checkpointer(settings) as checkpointer,
        open_trace_config(settings) as trace_config,
        open_db_pool(settings) as db_pool,
        open_archive_store(settings) as archive_store,
    ):
        vector_store = DocumentRepository(db_pool, build_embeddings(settings))
        retrieval_service = RetrievalService(
            vector_store=vector_store, top_k=settings.RAG.TOP_K
        )

        agent_service = AgentService(
            llm=build_llm(settings),
            checkpointer=checkpointer,
            trace_config=trace_config,
            retry_attempts=settings.LLM.RETRY_ATTEMPTS,
        )

        rag_service = RagService(
            retrieval_service=retrieval_service,
            agent_service=agent_service,
            max_revisions=settings.RAG.MAX_REVISIONS,
        )

        ingestion_service = IngestionService(
            index=vector_store,
            chunker=WholeDocumentChunker(),
            archives=archive_store,
            runs=IngestionRunRepository(db_pool),
        )

        auth_service = AuthService(
            user_repository=UserRepository(db_pool),
            pass_hasher=Argon2PasswordHasher(),
            token_codec=JwtTokenCodec(
                settings.AUTH.JWT_SECRET.get_secret_value(),
                settings.AUTH.JWT_ALGORITHM,
            ),
            access_ttl=timedelta(minutes=settings.AUTH.ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_ttl=timedelta(days=settings.AUTH.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        conversation_service = ConversationService(
            repository=ConversationRepository(
                db_pool, CheckpointHistoryStore(checkpointer)
            ),
            agent_service=agent_service,
        )

        yield Container(
            retrieval_service,
            agent_service,
            rag_service,
            ingestion_service,
            auth_service,
            conversation_service,
        )
