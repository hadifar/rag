from pydantic import BaseModel

from rag.config import AzureOpenAILLMConfig, OpenAILLMConfig, Settings


class SettingsResponse(BaseModel):
    model: str
    temperature: float
    top_k: int

    @classmethod
    def from_settings(cls, settings: Settings, top_k: int) -> "SettingsResponse":
        match settings.LLM:
            case OpenAILLMConfig() as llm:
                model = llm.MODEL
            case AzureOpenAILLMConfig() as llm:
                model = llm.DEPLOYMENT
        return cls(model=model, temperature=llm.TEMPERATURE, top_k=top_k)
