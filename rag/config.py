from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="forbid"
    )

    KNOWLEDGE_BASE_DIR: Path = Path("data")

    OPENAI_API_KEY: SecretStr
    OPENAI_MODEL: str

    PINECONE_API_KEY: SecretStr
    PINECONE_DENSE_INDEX_NAME: str
    PINECONE_SPARSE_INDEX_NAME: str
    PINECONE_CLOUD: str
    PINECONE_REGION: str
    PINECONE_DENSE_MODEL: str
    PINECONE_SPARSE_MODEL: str
    PINECONE_NAMESPACE: str

    OBSERVABILITY_BACKEND: Literal["logging", "langfuse"] = "logging"
    LANGFUSE_PUBLIC_KEY: SecretStr | None = None
    LANGFUSE_SECRET_KEY: SecretStr | None = None
    LANGFUSE_HOST: str | None = None

    CHECKPOINTER_BACKEND: Literal["memory", "postgres"] = "memory"
    DATABASE_URL: SecretStr | None = None

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @model_validator(mode="after")
    def _require_langfuse_credentials(self) -> "Settings":
        if self.OBSERVABILITY_BACKEND == "langfuse" and not (
            self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY and self.LANGFUSE_HOST
        ):
            raise ValueError(
                "LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST are required "
                "when OBSERVABILITY_BACKEND=langfuse"
            )
        return self

    @model_validator(mode="after")
    def _require_database_url(self) -> "Settings":
        if self.CHECKPOINTER_BACKEND == "postgres" and not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL is required when CHECKPOINTER_BACKEND=postgres"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
