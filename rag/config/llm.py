from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr


class _ChatModelConfig(BaseModel):
    """How the chat model is called, whichever backend serves it."""

    TEMPERATURE: float = Field(default=0.2, ge=0, le=2)
    # Tries per LLM call, in agents and guards, before falling back.
    RETRY_ATTEMPTS: int = Field(default=3, ge=1)


class OpenAILLMConfig(_ChatModelConfig):
    BACKEND: Literal["openai"] = "openai"
    API_KEY: SecretStr
    MODEL: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"


class AzureOpenAILLMConfig(_ChatModelConfig):
    BACKEND: Literal["azure_openai"] = "azure_openai"
    API_KEY: SecretStr
    ENDPOINT: str
    DEPLOYMENT: str
    API_VERSION: str
    EMBEDDING_DEPLOYMENT: str


LLMConfig = Annotated[
    OpenAILLMConfig | AzureOpenAILLMConfig, Field(discriminator="BACKEND")
]
