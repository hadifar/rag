from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)

from rag.config import AzureOpenAILLM, OpenAILLM, Settings

EMBEDDING_DIMENSIONS = 1536


def build_llm(settings: Settings) -> BaseChatModel:
    match settings.LLM:
        case OpenAILLM() as config:
            return ChatOpenAI(
                model=config.MODEL,
                api_key=config.API_KEY,
                streaming=True,
            )
        case AzureOpenAILLM() as config:
            return AzureChatOpenAI(
                azure_endpoint=config.ENDPOINT,
                azure_deployment=config.DEPLOYMENT,
                api_version=config.API_VERSION,
                api_key=config.API_KEY,
                streaming=True,
            )


def build_embeddings(settings: Settings) -> Embeddings:
    """Same provider and credentials as the chat model."""
    match settings.LLM:
        case OpenAILLM() as config:
            return OpenAIEmbeddings(
                model=config.EMBEDDING_MODEL,
                api_key=config.API_KEY,
                dimensions=EMBEDDING_DIMENSIONS,
            )
        case AzureOpenAILLM() as config:
            return AzureOpenAIEmbeddings(
                azure_endpoint=config.ENDPOINT,
                azure_deployment=config.EMBEDDING_DEPLOYMENT,
                api_version=config.API_VERSION,
                api_key=config.API_KEY,
                dimensions=EMBEDDING_DIMENSIONS,
            )
