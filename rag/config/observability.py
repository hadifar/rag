from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr


class LoggingObservabilityConfig(BaseModel):
    BACKEND: Literal["logging"] = "logging"


class LangfuseObservabilityConfig(BaseModel):
    BACKEND: Literal["langfuse"] = "langfuse"
    PUBLIC_KEY: SecretStr
    SECRET_KEY: SecretStr
    HOST: str


ObservabilityConfig = Annotated[
    LoggingObservabilityConfig | LangfuseObservabilityConfig,
    Field(discriminator="BACKEND"),
]
