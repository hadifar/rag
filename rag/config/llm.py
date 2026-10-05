from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr


class _ChatModelConfig(BaseModel):
    """How the chat model is called, whichever backend serves it."""

    TEMPERATURE: float = Field(default=0.2, ge=0, le=2)
    # Tries per LLM call before an agent's turn fails or a guard falls back.
    RETRY_ATTEMPTS: int = Field(default=3, ge=1)
    # Times the groundedness guard sends an answer back per turn; 0 only verifies.
    MAX_REVISIONS: int = Field(default=1, ge=0)
    # Set only for a reasoning model (e.g. gpt-5-mini, o4-mini): switches to the
    # Responses API so its reasoning summary streams to the user. TEMPERATURE is then
    # ignored, since reasoning models reject it.
    REASONING_EFFORT: Literal["minimal", "low", "medium", "high"] | None = None


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
