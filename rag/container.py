from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.adapters.argon2 import Argon2PasswordHasher
from rag.adapters.jwt_codec import JwtTokenCodec
from rag.adapters.kb_archive_store import open_archive_store
from rag.adapters.langchain.llm_client import build_embeddings, build_llms
from rag.adapters.langchain.observability import open_trace_config
from rag.adapters.postgres_db import open_db_pool
from rag.config import Settings
from rag.domain.models import (
    DEFAULT_MODEL,
    AppSettings,
    Chunk,
    InputVerdict,
    UploadLimits,
)
from rag.domain.ports import CachePort
from rag.repository.attachment_repository import AttachmentRepository
from rag.repository.cache_repository import (
    EmbeddingCacheRepository,
    InputVerdictCacheRepository,
    NoCache,
    SearchCacheRepository,
)
from rag.repository.conversation_repository import ConversationRepository
from rag.repository.document_repository import DocumentRepository
from rag.repository.ingestion_run_repository import IngestionRunRepository
from rag.repository.share_repository import ShareRepository
from rag.repository.skill_repository import SkillRepository
from rag.repository.user_repository import UserRepository
from rag.services.agent_service.agent import RagAgent
from rag.services.agent_service.history import HistoryLimits
from rag.services.agent_service.llm import Llm
from rag.services.attachment_service.service import AttachmentService
from rag.services.auth_service.service import AuthService
from rag.services.chat_service.service import ChatService
from rag.services.conversation_service.service import ConversationService
from rag.services.ingestion_service.chunking import WholeDocumentChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.retrieval_service.caching import CachedEmbeddings
from rag.services.retrieval_service.reranking import LlmReranker, NoReranker
from rag.services.retrieval_service.service import RetrievalService
from rag.services.run_settings_service.service import RunSettingsService
from rag.services.share_service.service import ShareService
from rag.services.skill_service.service import SkillService


@dataclass
class Container:
    retrieval_service: RetrievalService
    ingestion_service: IngestionService
    auth_service: AuthService
    conversation_service: ConversationService
    chat_service: ChatService
    share_service: ShareService
    attachment_service: AttachmentService
    skill_service: SkillService
    run_settings_service: RunSettingsService
    app_settings: AppSettings


@dataclass
class _Caches:
    embeddings: CachePort[list[float]]
    search: CachePort[list[tuple[Chunk, float]]]
    verdicts: CachePort[InputVerdict]


def _caches(
    settings: Settings, db_pool: AsyncConnectionPool[AsyncConnection]
) -> _Caches:
    """Each cache keyed by the model that fills it; a search's also by the settings
    that shape its result.
    """
    if not settings.CACHE.ENABLED:
        return _Caches(embeddings=NoCache(), search=NoCache(), verdicts=NoCache())

    cache, llm, retrieval = settings.CACHE, settings.LLM, settings.RETRIEVAL
    reranker = DEFAULT_MODEL if retrieval.RERANK_CANDIDATES else "none"
    return _Caches(
        embeddings=EmbeddingCacheRepository(
            db_pool,
            model=llm.embedding_model_name,
            ttl=timedelta(days=cache.EMBEDDING_TTL_DAYS),
        ),
        search=SearchCacheRepository(
            db_pool,
            model=llm.embedding_model_name,
            ttl=timedelta(days=cache.SEARCH_TTL_DAYS),
            scope=(
                f"candidates={retrieval.RETRIEVAL_CANDIDATES};"
                f"rerank_candidates={retrieval.RERANK_CANDIDATES};"
                f"summary_weight={retrieval.SUMMARY_WEIGHT};reranker={reranker}"
            ),
        ),
        verdicts=InputVerdictCacheRepository(
            db_pool,
            model=DEFAULT_MODEL,
            ttl=timedelta(days=cache.VERDICT_TTL_DAYS),
        ),
    )


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container, None]:  # noqa
    """Opens connections and tears it down on exit."""

    async with (
        open_trace_config(settings) as trace_config,
        open_db_pool(settings) as db_pool,
        open_archive_store(settings) as archive_store,
    ):
        caches = _caches(settings, db_pool)
        vector_store = DocumentRepository(
            db_pool,
            CachedEmbeddings(build_embeddings(settings), caches.embeddings),
            summary_weight=settings.RETRIEVAL.SUMMARY_WEIGHT,
        )
        llm = Llm(
            models=build_llms(settings),
            trace_config=trace_config,
            attempts=settings.LLM.RETRY_ATTEMPTS,
            reasoning=settings.LLM.REASONING_EFFORT is not None,
        )

        retrieval_service = RetrievalService(
            vector_store=vector_store,
            reranker=(
                LlmReranker(llm)
                if settings.RETRIEVAL.RERANK_CANDIDATES
                else NoReranker()
            ),
            candidates=settings.RETRIEVAL.RETRIEVAL_CANDIDATES,
            rerank_candidates=settings.RETRIEVAL.RERANK_CANDIDATES,
            cache=caches.search,
        )

        skill_repo = SkillRepository(db_pool)
        uploads = UploadLimits(**{k.lower(): v for k, v in settings.UPLOADS})
        skill_service = SkillService(
            skills=skill_repo,
            max_skill_bytes=uploads.skill_max_bytes,
            max_archive_bytes=uploads.skill_archive_max_bytes,
        )

        rag_agent = RagAgent(
            llm=llm,
            search=retrieval_service,
            skills=skill_repo,
            verdicts=caches.verdicts,
            history_limits=HistoryLimits(
                max_tokens=settings.LLM.HISTORY_MAX_TOKENS,
                max_turns=settings.LLM.HISTORY_MAX_TURNS,
            ),
        )

        ingestion_service = IngestionService(
            index=vector_store,
            chunker=WholeDocumentChunker(),
            archives=archive_store,
            runs=IngestionRunRepository(db_pool),
            max_archive_bytes=uploads.kb_max_bytes,
        )

        user_repo = UserRepository(db_pool)
        auth_service = AuthService(
            user_repository=user_repo,
            pass_hasher=Argon2PasswordHasher(),
            token_codec=JwtTokenCodec(
                settings.AUTH.JWT_SECRET.get_secret_value(),
                settings.AUTH.JWT_ALGORITHM,
            ),
            access_ttl=timedelta(minutes=settings.AUTH.ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_ttl=timedelta(days=settings.AUTH.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        conversation_repo = ConversationRepository(db_pool)
        attachment_repo = AttachmentRepository(db_pool)
        conversation_service = ConversationService(
            repository=conversation_repo,
            llm=llm,
        )

        chat_service = ChatService(
            repository=conversation_repo,
            attachments=attachment_repo,
            users=user_repo,
            agent=rag_agent,
        )

        yield Container(
            retrieval_service=retrieval_service,
            ingestion_service=ingestion_service,
            auth_service=auth_service,
            conversation_service=conversation_service,
            chat_service=chat_service,
            share_service=ShareService(
                shares=ShareRepository(db_pool),
                conversations=conversation_repo,
            ),
            attachment_service=AttachmentService(
                attachments=attachment_repo,
                conversations=conversation_repo,
                max_bytes=uploads.attachment_max_bytes,
            ),
            skill_service=skill_service,
            run_settings_service=RunSettingsService(users=user_repo),
            app_settings=AppSettings(
                model=DEFAULT_MODEL,
                top_k=retrieval_service.top_k,
                uploads=uploads,
            ),
        )
