from pydantic import BaseModel

from rag.config import AzureOpenAILLMConfig, OpenAILLMConfig, Settings


class UploadLimitsResponse(BaseModel):
    """The largest file each upload takes, in bytes (the `UPLOADS__*` settings)."""

    kb_max_bytes: int
    skill_max_bytes: int
    skill_archive_max_bytes: int
    attachment_max_bytes: int


class SettingsResponse(BaseModel):
    model: str
    top_k: int
    uploads: UploadLimitsResponse

    @classmethod
    def from_settings(cls, settings: Settings, top_k: int) -> "SettingsResponse":
        match settings.LLM:
            case OpenAILLMConfig() as llm:
                model = llm.MODEL
            case AzureOpenAILLMConfig() as llm:
                model = llm.DEPLOYMENT
        uploads = UploadLimitsResponse(
            **{name.lower(): value for name, value in settings.UPLOADS}
        )
        return cls(model=model, top_k=top_k, uploads=uploads)
