from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    CHAT_MODEL: str = "gpt-4o-mini"

    KNOWLEDGE_BASE_DIR: Path = Path("data")
    CHECKPOINTER_BACKEND: str = "memory"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
