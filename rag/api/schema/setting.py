from pydantic import BaseModel, ConfigDict

from rag.domain.models import Effort, ModelName, RunSettingsUpdate


class UploadLimitsResponse(BaseModel):
    """The largest file each upload takes, in bytes."""

    model_config = ConfigDict(from_attributes=True)

    kb_max_bytes: int
    skill_max_bytes: int
    skill_archive_max_bytes: int
    attachment_max_bytes: int


class SettingsResponse(BaseModel):
    """How the app is configured, as far as its users need to know."""

    model_config = ConfigDict(from_attributes=True)

    model: str
    top_k: int
    uploads: UploadLimitsResponse


class RunSettingsResponse(BaseModel):
    """What the user's chat turns run on, in every conversation."""

    model_config = ConfigDict(from_attributes=True)

    model: ModelName
    effort: Effort


class RunSettingsUpdateRequest(BaseModel):
    """The fields to change; each one left out stays as is."""

    model: ModelName | None = None
    effort: Effort | None = None

    def to_update(self) -> RunSettingsUpdate:
        return RunSettingsUpdate(**self.model_dump())
