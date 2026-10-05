from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

from rag.adapters.argon2 import Argon2PasswordHasher
from rag.adapters.jwt_codec import JwtTokenCodec
from rag.adapters.kb_archive_store import open_archive_store
from rag.adapters.lang_llm_client import build_embeddings, build_llm
from rag.adapters.lang_memory import open_checkpointer
from rag.adapters.lang_observability import open_trace_config
from rag.adapters.postgres_db import open_db_pool
from rag.config import Settings
from rag.repository.conversation_repository import ConversationRepository
from rag.repository.document_repository import DocumentRepository
from rag.repository.ingestion_run_repository import IngestionRunRepository
from rag.repository.preference_repository import PreferenceRepository
from rag.repository.transcript_repository import TranscriptRepository
from rag.repository.user_repository import UserRepository
from rag.services.agent_service.service import AgentService
from rag.services.auth_service.service import AuthService
from rag.services.conversation_service.service import ConversationService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.preference_service.service import PreferenceService
from rag.services.rag_service.service import RagService
from rag.services.retrieval_service.reranking import LlmReranker, NoReranker
from rag.services.retrieval_service.service import RetrievalService


@dataclass
class Container:
    retrieval_service: RetrievalService
    preference_service: PreferenceService
    rag_service: RagService
    ingestion_service: IngestionService
    auth_service: AuthService
    conversation_service: ConversationService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container, None]:
    """Opens connections and tears it down on exit."""

    async with (
        open_checkpointer(settings) as checkpointer,
        open_trace_config(settings) as trace_config,
        open_db_pool(settings) as db_pool,
        open_archive_store(settings) as archive_store,
    ):
        vector_store = DocumentRepository(
            db_pool,
            build_embeddings(settings),
            summary_weight=settings.RETRIEVAL.SUMMARY_WEIGHT,
        )
        agent_service = AgentService(
            llm=build_llm(settings),
            checkpointer=checkpointer,
            trace_config=trace_config,
            retry_attempts=settings.LLM.RETRY_ATTEMPTS,
        )

        retrieval_service = RetrievalService(
            vector_store=vector_store,
            reranker=(
                LlmReranker(agent_service, attempts=settings.LLM.RETRY_ATTEMPTS)
                if settings.RETRIEVAL.RERANK
                else NoReranker()
            ),
            top_k=settings.RAG.TOP_K,
            # without a reranker, there is nothing to fetch beyond the top_k for
            candidates=(
                settings.RETRIEVAL.RERANK_CANDIDATES if settings.RETRIEVAL.RERANK else 0
            ),
        )

        preference_service = PreferenceService(repository=PreferenceRepository(db_pool))

        rag_service = RagService(
            retrieval_service=retrieval_service,
            agent_service=agent_service,
            max_revisions=settings.RAG.MAX_REVISIONS,
            capabilities=[preference_service.capability()],
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
            repository=ConversationRepository(db_pool),
            transcript=TranscriptRepository(db_pool),
            chat_agent=rag_service,
            agent_service=agent_service,
        )

        yield Container(
            retrieval_service=retrieval_service,
            preference_service=preference_service,
            rag_service=rag_service,
            ingestion_service=ingestion_service,
            auth_service=auth_service,
            conversation_service=conversation_service,
        )
