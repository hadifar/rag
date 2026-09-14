from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from rag.config import Settings


def build_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL, api_key=SecretStr(settings.OPENAI_API_KEY)
    )
