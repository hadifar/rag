from pydantic import BaseModel, ConfigDict


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
