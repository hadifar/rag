from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    OPENAI_API_KEY: str
    OPENAI_MODEL: str

    PINECONE_API_KEY: str
    PINECONE_DENSE_INDEX_NAME: str
    PINECONE_SPARSE_INDEX_NAME: str
    PINECONE_CLOUD: str
    PINECONE_REGION: str
    PINECONE_DENSE_MODEL: str
    PINECONE_SPARSE_MODEL: str
    PINECONE_NAMESPACE: str

    LANGFUSE_ENABLED: bool
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_HOST: str

    KNOWLEDGE_BASE_DIR: Path = Path("data")

    CHECKPOINTER_BACKEND: Literal["memory", "postgres"] = "memory"
    DATABASE_URL: str | None = None

    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
