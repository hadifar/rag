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


def build_llm(settings: Settings) -> BaseChatModel:
    match settings.LLM:
        case OpenAILLMConfig() as config:
            return ChatOpenAI(
                model=config.MODEL,
                api_key=config.API_KEY,
                temperature=config.TEMPERATURE,
                streaming=True,
            )
        case AzureOpenAILLMConfig() as config:
            return AzureChatOpenAI(
                azure_endpoint=config.ENDPOINT,
                azure_deployment=config.DEPLOYMENT,
                api_version=config.API_VERSION,
                api_key=config.API_KEY,
                temperature=config.TEMPERATURE,
                streaming=True,
            )


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
