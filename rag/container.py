from dataclasses import dataclass

from rag.adapters.checkpointer import build_checkpointer
from rag.adapters.embedding_client import build_embeddings
from rag.adapters.llm_client import build_llm
from rag.adapters.pinecone_client import build_vector_store
from rag.config import Settings
from rag.services.embedding_service.service import EmbeddingService
from rag.services.generation_service.service import GenerationService
from rag.services.ingestion_service.chunking import MarkdownHeaderChunker
from rag.services.ingestion_service.service import IngestionService
from rag.services.ranking_service.service import RankingService


@dataclass
class Container:
    embedding_service: EmbeddingService
    ranking_service: RankingService
    generation_service: GenerationService
    ingestion_service: IngestionService


def build_container(settings: Settings) -> Container:
    embeddings = build_embeddings(settings)
    embedding_service = EmbeddingService(embedder=embeddings)

    vector_store = build_vector_store(settings, embeddings)
    ranking_service = RankingService(vector_store=vector_store)

    generation_service = GenerationService(
        llm=build_llm(settings),
        ranking_service=ranking_service,
        checkpointer=build_checkpointer(settings),
    )

    ingestion_service = IngestionService(
        vector_store=vector_store, chunker=MarkdownHeaderChunker()
    )

    return Container(
        embedding_service, ranking_service, generation_service, ingestion_service
    )
