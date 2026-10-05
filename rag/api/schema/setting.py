from pydantic import BaseModel, ConfigDict, Field

from rag.config import AzureOpenAILLMConfig, OpenAILLMConfig, Settings
from rag.api.schema.text import UserText
from rag.domain.models import MAX_PREFERENCE_LENGTH


class SettingsResponse(BaseModel):
    model: str
    temperature: float
    top_k: int

    @classmethod
    def from_settings(cls, settings: Settings) -> "SettingsResponse":
        match settings.LLM:
            case OpenAILLMConfig() as llm:
                model = llm.MODEL
            case AzureOpenAILLMConfig() as llm:
                model = llm.DEPLOYMENT
        return cls(
            model=model, temperature=llm.TEMPERATURE, top_k=settings.RETRIEVAL.top_k
        )


class PreferenceRequest(BaseModel):
    text: UserText = Field(min_length=1, max_length=MAX_PREFERENCE_LENGTH)


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
