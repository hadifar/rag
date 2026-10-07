from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag.config.auth import AuthConfig
from rag.config.cache import CacheConfig
from rag.config.kb_storage import KbStorageConfig, LocalKbStorageConfig
from rag.config.llm import LLMConfig
from rag.config.observability import LoggingObservabilityConfig, ObservabilityConfig
from rag.config.retrieval import RetrievalConfig
from rag.config.uploads import UploadsConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", case_sensitive=True, extra="forbid"
    )

    # The one Postgres database behind everything: users, conversations and their
    # turns, knowledge-base chunks; its schema is Alembic's.
    DATABASE_URL: SecretStr

    AUTH: AuthConfig

    # What `rag ingest` reads by default: a .zip of .md files, or a directory of them.
    KNOWLEDGE_BASE_SOURCE: Path = Path("data/data.zip")
    # Where uploaded knowledge-base zips are kept, so the index can be rebuilt from them.
    KB_STORAGE: KbStorageConfig = LocalKbStorageConfig()

    LLM: LLMConfig
    RETRIEVAL: RetrievalConfig = RetrievalConfig()
    CACHE: CacheConfig = CacheConfig()
    OBSERVABILITY: ObservabilityConfig = LoggingObservabilityConfig()
    UPLOADS: UploadsConfig = UploadsConfig()

    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
