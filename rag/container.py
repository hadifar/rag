from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

from rag.adapters.argon2 import Argon2PasswordHasher
from rag.adapters.jwt_codec import JwtTokenCodec
from rag.adapters.kb_archive_store import open_archive_store
from rag.adapters.langchain.llm_client import build_embeddings, build_llm
from rag.adapters.langchain.observability import open_trace_config
from rag.adapters.postgres_db import open_db_pool
from rag.config import Settings
from rag.repository.conversation_repository import ConversationRepository
from rag.repository.document_repository import DocumentRepository
from rag.repository.ingestion_run_repository import IngestionRunRepository
from rag.repository.user_repository import UserRepository
from rag.services.agent_service.agent import ChatAgent
from rag.services.agent_service.service import AgentService
from rag.services.auth_service.service import AuthService
from rag.services.chat_service.service import ChatService
from rag.services.conversation_service.service import ConversationService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.reranking import LlmReranker, NoReranker
from rag.services.retrieval_service.service import RetrievalService


@dataclass
class Container:
    retrieval_service: RetrievalService
    ingestion_service: IngestionService
    auth_service: AuthService
    conversation_service: ConversationService
    chat_service: ChatService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container, None]:  # noqa
    """Opens connections and tears it down on exit."""

    async with (
        open_trace_config(settings) as trace_config,
        open_db_pool(settings) as db_pool,
        open_archive_store(settings) as archive_store,
    ):
        vector_store = DocumentRepository(
            db_pool,
            build_embeddings(settings),
            summary_weight=settings.RETRIEVAL.SUMMARY_WEIGHT,
        )
        llm = build_llm(settings)
        llm_service = AgentService(llm=llm, trace_config=trace_config)

        retrieval_service = RetrievalService(
            vector_store=vector_store,
            reranker=(
                LlmReranker(llm_service, attempts=settings.LLM.RETRY_ATTEMPTS)
                if settings.RETRIEVAL.rerank
                else NoReranker()
            ),
            top_k=settings.RETRIEVAL.top_k,
            candidates=settings.RETRIEVAL.RETRIEVAL_CANDIDATES,
        )

        chat_agent = ChatAgent(
            llm=llm,
            search=retrieval_service,
            trace_config=trace_config,
            retry_attempts=settings.LLM.RETRY_ATTEMPTS,
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

        conversation_repo = ConversationRepository(db_pool)
        conversation_service = ConversationService(
            repository=conversation_repo,
            llm_service=llm_service,
        )

        chat_service = ChatService(
            repository=conversation_repo,
            chat_agent=chat_agent,
        )

        yield Container(
            retrieval_service=retrieval_service,
            ingestion_service=ingestion_service,
            auth_service=auth_service,
            conversation_service=conversation_service,
            chat_service=chat_service,
        )
