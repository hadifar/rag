from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_DENSE_INDEX_NAME: str
    PINECONE_SPARSE_INDEX_NAME: str
    PINECONE_CLOUD: str
    PINECONE_REGION: str
    PINECONE_NAMESPACE: str = "default"
    PINECONE_DENSE_MODEL: str = "llama-text-embed-v2"
    PINECONE_SPARSE_MODEL: str = "pinecone-sparse-english-v0"

    CHAT_MODEL: str = "gpt-4o-mini"

    KNOWLEDGE_BASE_DIR: Path = Path("data")

    CHECKPOINTER_BACKEND: str = "memory"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
