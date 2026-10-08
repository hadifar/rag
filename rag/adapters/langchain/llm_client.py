from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)

from rag.config import AzureOpenAILLMConfig, OpenAILLMConfig, Settings
from rag.domain.models import MODEL_NAMES, ModelName
from rag.domain.ports import EmbeddingsPort

EMBEDDING_DIMENSIONS = 1536


def build_llms(settings: Settings) -> dict[ModelName, BaseChatModel]:
    """One chat model per name a conversation can be set to."""
    return {model: _build_llm(settings, model) for model in MODEL_NAMES}


def _build_llm(settings: Settings, model: ModelName) -> BaseChatModel:
    """`model`; for Azure, the deployment of that name."""
    match settings.LLM:
        case OpenAILLMConfig() as config:
            return ChatOpenAI(
                model=model,
                api_key=config.API_KEY,
                streaming=True,
                **_sampling(config),
            )
        case AzureOpenAILLMConfig() as config:
            return AzureChatOpenAI(
                azure_endpoint=config.ENDPOINT,
                azure_deployment=model,
                api_version=config.API_VERSION,
                api_key=config.API_KEY,
                streaming=True,
                **_sampling(config),
            )


def _sampling(config: OpenAILLMConfig | AzureOpenAILLMConfig) -> dict[str, Any]:
    """Nothing for a plain chat model; for a reasoning model, the Responses API with a
    reasoning summary, which is the only way OpenAI returns any reasoning text.
    """
    if config.REASONING_EFFORT is None:
        return {}
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
