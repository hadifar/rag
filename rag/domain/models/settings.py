from dataclasses import dataclass


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

    model: str  # the chat model's name (its deployment's, on Azure)
    top_k: int  # passages a knowledge-base search returns
    uploads: UploadLimits
