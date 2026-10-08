from dataclasses import dataclass

from rag.domain.models.agent.agent import Effort, ModelName


@dataclass(frozen=True)
class UploadLimits:
    """The largest file each upload takes, in bytes."""

    kb_max_bytes: int  # a knowledge-base .zip
    skill_max_bytes: int  # a SKILL.md file, alone or inside an archive
    skill_archive_max_bytes: int  # a .zip or .skill archive, as uploaded
    attachment_max_bytes: int  # any chat attachment


@dataclass(frozen=True)
class AppSettings:
    """What the app tells its users about how it's configured; no secrets."""

    model: str  # the default chat model's name (the guards' and titles')
    top_k: int  # passages a knowledge-base search returns
    uploads: UploadLimits


@dataclass(frozen=True)
class RunSettingsUpdate:
    """What to change about the model and effort a user's turns run on; a field left
    None stays as is.
    """

    model: ModelName | None = None
    effort: Effort | None = None
