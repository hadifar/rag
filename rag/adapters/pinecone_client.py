from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from rag.config import Settings


def build_vector_store(
    settings: Settings, embeddings: OpenAIEmbeddings
) -> PineconeVectorStore:
    """Idempotent: connects to an existing index by name, creates it only if missing."""
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    if not pc.has_index(settings.PINECONE_INDEX_NAME):
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=settings.EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION
            ),
        )

    index = pc.Index(settings.PINECONE_INDEX_NAME)
    return PineconeVectorStore(index=index, embedding=embeddings)
