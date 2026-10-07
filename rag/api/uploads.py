"""The files routers take: each upload read from the request as a domain `Upload`, no
further than its limit in `UPLOADS` allows.
"""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, UploadFile

from rag.api.deps import SettingsDep
from rag.config import UploadsConfig
from rag.domain.models import Upload


def _capped(limit: Callable[[UploadsConfig], int]) -> Any:
    """A dependency on the request's `file`, read up to one byte past its `limit`:
    enough for the service to reject it, without ever holding an oversized one in
    memory.
    """

    async def read(file: UploadFile, settings: SettingsDep) -> Upload:
        max_bytes = limit(settings.UPLOADS)
        return Upload(file.filename or "", await file.read(max_bytes + 1))

    return Depends(read)


ArchiveUpload = Annotated[Upload, _capped(lambda u: u.KB_MAX_BYTES)]
SkillUpload = Annotated[
    Upload, _capped(lambda u: max(u.SKILL_MAX_BYTES, u.SKILL_ARCHIVE_MAX_BYTES))
]
AttachmentUpload = Annotated[Upload, _capped(lambda u: u.ATTACHMENT_MAX_BYTES)]
