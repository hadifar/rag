from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from psycopg.conninfo import make_conninfo
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """The one Postgres database behind everything: users, conversations, knowledge-base
    chunks (schema by Alembic) and conversation messages (LangGraph's checkpointer).

    Split into fields rather than one URL so the host (plain config, e.g. `postgres` inside
    Docker Compose) can be overridden on its own, and only PASSWORD is a secret.
    """

    HOST: str = "localhost"
    PORT: int = 5432
    NAME: str = "rag"
    USER: str = "rag"
    PASSWORD: SecretStr
    # Secure by default: TLS, with the server's certificate checked against the system's
    # CAs. Only a local or CI database without TLS sets "disable".
    SSLMODE: Literal["disable", "verify-full"] = "verify-full"

    def connect_kwargs(self) -> dict[str, str | int]:
        """libpq connection parameters, for psycopg (`psycopg.connect(**kwargs)`)."""
        kwargs: dict[str, str | int] = {
            "host": self.HOST,
            "port": self.PORT,
            "dbname": self.NAME,
            "user": self.USER,
            "password": self.PASSWORD.get_secret_value(),
            "sslmode": self.SSLMODE,
        }
        if self.SSLMODE == "verify-full":
            kwargs["sslrootcert"] = "system"
        return kwargs

    def conninfo(self) -> str:
        """The same parameters as a libpq conninfo string, quoted safely, for pools."""
        return make_conninfo("", **self.connect_kwargs())


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


LLMConfig = Annotated[OpenAILLM | AzureOpenAILLM, Field(discriminator="BACKEND")]

ObservabilityConfig = Annotated[
    LoggingObservability | LangfuseObservability, Field(discriminator="BACKEND")
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", case_sensitive=True, extra="forbid"
    )

    DATABASE: DatabaseConfig

    AUTH: AuthConfig

    KNOWLEDGE_BASE_DIR: Path = Path("data")

    LLM: LLMConfig
    OBSERVABILITY: ObservabilityConfig = LoggingObservability()

    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] — fields are populated from .env
