from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr


class _ChatModelConfig(BaseModel):
    """How the chat model is called, whichever backend serves it."""

    # Tries per LLM call before an agent's turn fails or a guard falls back.
    RETRY_ATTEMPTS: int = Field(default=3, ge=1)
    # How much of the earlier turns the agent rereads each model call: past either
    # limit, the oldest turns are left out. Keep the tokens (approximate) well under
    # the model's context window.
    HISTORY_MAX_TOKENS: int = Field(default=16_000, ge=0)
    HISTORY_MAX_TURNS: int = Field(default=20, ge=0)
    # Set only for a reasoning model (e.g. gpt-5-mini, o4-mini): switches to the
    # Responses API so its reasoning summary streams to the user.
    REASONING_EFFORT: Literal["minimal", "low", "medium", "high"] | None = None


class OpenAILLMConfig(_ChatModelConfig):
    BACKEND: Literal["openai"] = "openai"
    API_KEY: SecretStr
    MODEL: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    @property
    def chat_model_name(self) -> str:
        return self.MODEL

    @property
    def embedding_model_name(self) -> str:
        return self.EMBEDDING_MODEL


class AzureOpenAILLMConfig(_ChatModelConfig):
    BACKEND: Literal["azure_openai"] = "azure_openai"
    API_KEY: SecretStr
    ENDPOINT: str
    DEPLOYMENT: str
    API_VERSION: str
    EMBEDDING_DEPLOYMENT: str

    # A deployment names the model it serves.
    @property
    def chat_model_name(self) -> str:
        return self.DEPLOYMENT

    @property
    def embedding_model_name(self) -> str:
        return self.EMBEDDING_DEPLOYMENT


LLMConfig = Annotated[
    OpenAILLMConfig | AzureOpenAILLMConfig, Field(discriminator="BACKEND")
]
