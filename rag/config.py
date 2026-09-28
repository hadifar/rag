from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseModel):
    JWT_SECRET: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


class OpenAILLM(BaseModel):
    BACKEND: Literal["openai"] = "openai"
    API_KEY: SecretStr
    MODEL: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"


class AzureOpenAILLM(BaseModel):
    BACKEND: Literal["azure_openai"] = "azure_openai"
    API_KEY: SecretStr
    ENDPOINT: str
    DEPLOYMENT: str
    API_VERSION: str
    EMBEDDING_DEPLOYMENT: str


class LoggingObservability(BaseModel):
    BACKEND: Literal["logging"] = "logging"


class LangfuseObservability(BaseModel):
    BACKEND: Literal["langfuse"] = "langfuse"
    PUBLIC_KEY: SecretStr
    SECRET_KEY: SecretStr
    HOST: str


class LocalKbStorage(BaseModel):
    BACKEND: Literal["local"] = "local"
    DIR: Path = Path("data/uploads")


class AzureBlobKbStorage(BaseModel):
    """Authenticates with DefaultAzureCredential: the Web App's managed identity in
    Azure, `az login` locally — no keys.
    """

    BACKEND: Literal["azure_blob"] = "azure_blob"
    ACCOUNT_URL: str  # https://<account>.blob.core.windows.net
    CONTAINER: str = "kb-archives"


LLMConfig = Annotated[OpenAILLM | AzureOpenAILLM, Field(discriminator="BACKEND")]

KbStorageConfig = Annotated[
    LocalKbStorage | AzureBlobKbStorage, Field(discriminator="BACKEND")
]

ObservabilityConfig = Annotated[
    LoggingObservability | LangfuseObservability, Field(discriminator="BACKEND")
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", case_sensitive=True, extra="forbid"
    )

    # The one Postgres database behind everything: users, conversations, knowledge-base
    # chunks (schema by Alembic) and conversation messages (LangGraph's checkpointer).
    DATABASE_URL: SecretStr

    AUTH: AuthConfig

    # What `rag ingest` reads by default: a .zip of .md files, or a directory of them.
    KNOWLEDGE_BASE_SOURCE: Path = Path("data/data.zip")
    # Where uploaded knowledge-base zips are kept, so the index can be rebuilt from them.
    KB_STORAGE: KbStorageConfig = LocalKbStorage()

    LLM: LLMConfig
    OBSERVABILITY: ObservabilityConfig = LoggingObservability()

    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
