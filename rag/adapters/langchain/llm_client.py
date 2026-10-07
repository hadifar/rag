from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)

from rag.config import AzureOpenAILLMConfig, OpenAILLMConfig, Settings
from rag.domain.ports import EmbeddingsPort

EMBEDDING_DIMENSIONS = 1536


def build_llm(settings: Settings, model: str | None = None) -> BaseChatModel:
    """The main chat model (MODEL or DEPLOYMENT), or `model`, one a user picks: for
    Azure, the name of its deployment.
    """
    match settings.LLM:
        case OpenAILLMConfig() as config:
            return ChatOpenAI(
                model=model or config.MODEL,
                api_key=config.API_KEY,
                streaming=True,
                **_sampling(config),
            )
        case AzureOpenAILLMConfig() as config:
            return AzureChatOpenAI(
                azure_endpoint=config.ENDPOINT,
                azure_deployment=model or config.DEPLOYMENT,
                api_version=config.API_VERSION,
                api_key=config.API_KEY,
                streaming=True,
                **_sampling(config),
            )


def _sampling(config: OpenAILLMConfig | AzureOpenAILLMConfig) -> dict[str, Any]:
    """Temperature for a plain chat model; for a reasoning model, the Responses API
    with a reasoning summary, which is the only way OpenAI returns any reasoning text.
    """
    if config.REASONING_EFFORT is None:
        return {"temperature": config.TEMPERATURE}
    return {
        "use_responses_api": True,
        "reasoning": {"effort": config.REASONING_EFFORT, "summary": "auto"},
    }


def build_embeddings(settings: Settings) -> EmbeddingsPort:
    """Same provider and credentials as the chat model."""
    match settings.LLM:
        case OpenAILLMConfig() as config:
            return OpenAIEmbeddings(
                model=config.EMBEDDING_MODEL,
                api_key=config.API_KEY,
                dimensions=EMBEDDING_DIMENSIONS,
            )
        case AzureOpenAILLMConfig() as config:
            return AzureOpenAIEmbeddings(
                azure_endpoint=config.ENDPOINT,
                azure_deployment=config.EMBEDDING_DEPLOYMENT,
                api_version=config.API_VERSION,
                api_key=config.API_KEY,
                dimensions=EMBEDDING_DIMENSIONS,
            )
