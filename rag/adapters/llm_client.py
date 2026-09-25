from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from rag.config import AzureOpenAILLM, OpenAILLM, Settings


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
