from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAILLM(BaseModel):
    BACKEND: Literal["openai"] = "openai"
    API_KEY: SecretStr
    MODEL: str


class AzureOpenAILLM(BaseModel):
    BACKEND: Literal["azure_openai"] = "azure_openai"
    API_KEY: SecretStr
    ENDPOINT: str
    DEPLOYMENT: str
    API_VERSION: str


class MemoryCheckpointer(BaseModel):
    BACKEND: Literal["memory"] = "memory"


class PostgresCheckpointer(BaseModel):
    BACKEND: Literal["postgres"] = "postgres"
    DATABASE_URL: SecretStr


class LoggingObservability(BaseModel):
    BACKEND: Literal["logging"] = "logging"


class LangfuseObservability(BaseModel):
    BACKEND: Literal["langfuse"] = "langfuse"
    PUBLIC_KEY: SecretStr
    SECRET_KEY: SecretStr
    HOST: str


LLMConfig = Annotated[OpenAILLM | AzureOpenAILLM, Field(discriminator="BACKEND")]

ObservabilityConfig = Annotated[
    LoggingObservability | LangfuseObservability, Field(discriminator="BACKEND")
]

CheckpointerConfig = Annotated[
    MemoryCheckpointer | PostgresCheckpointer, Field(discriminator="BACKEND")
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", case_sensitive=True, extra="forbid"
    )

    KNOWLEDGE_BASE_DIR: Path = Path("data")

    LLM: LLMConfig

    PINECONE_API_KEY: SecretStr
    PINECONE_DENSE_INDEX_NAME: str
    PINECONE_SPARSE_INDEX_NAME: str
    PINECONE_CLOUD: str
    PINECONE_REGION: str
    PINECONE_DENSE_MODEL: str
    PINECONE_SPARSE_MODEL: str
    PINECONE_NAMESPACE: str

    OBSERVABILITY: ObservabilityConfig = LoggingObservability()
    CHECKPOINTER: CheckpointerConfig = MemoryCheckpointer()

    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
