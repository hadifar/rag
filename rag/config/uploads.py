from pydantic import BaseModel, Field


class UploadsConfig(BaseModel):
    """The largest file each upload takes, in bytes: the API reads no further, and the
    service rejects anything over it. nginx caps each request body from the same env
    vars (infra/docker/upload-limits.envsh), so docker-compose.yml and main.bicep set
    them all, to these defaults (tests/unit/test_upload_limits.py).
    """

    # A knowledge-base .zip of .md files.
    KB_MAX_BYTES: int = Field(default=20 * 1024 * 1024, ge=1)
    # A SKILL.md file, alone or inside an archive.
    SKILL_MAX_BYTES: int = Field(default=50 * 1024, ge=1)
    # A .zip or .skill archive of a SKILL.md with its reference files, as uploaded.
    SKILL_ARCHIVE_MAX_BYTES: int = Field(default=512 * 1024, ge=1)
    # Any chat attachment; each kind may cap it lower (attachment_service/kinds.py).
    ATTACHMENT_MAX_BYTES: int = Field(default=5 * 1024 * 1024, ge=1)
