from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from rag.config import Settings


def build_llm(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.CHAT_MODEL,
        api_key=SecretStr(settings.OPENAI_API_KEY),
        streaming=True,
    )
