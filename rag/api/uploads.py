from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, UploadFile

from rag.api.deps import AppSettingsDep
from rag.domain.models import Upload, UploadLimits


def _capped(limit: Callable[[UploadLimits], int]) -> Any:
    """A dependency on the request's `file`, read up to one byte past its `limit`:
    enough for the service to reject it, without ever holding an oversized one in
    memory.
    """

    async def read(file: UploadFile, app_settings: AppSettingsDep) -> Upload:
        max_bytes = limit(app_settings.uploads)
        return Upload(file.filename or "", await file.read(max_bytes + 1))

    return Depends(read)


ArchiveUpload = Annotated[Upload, _capped(lambda u: u.kb_max_bytes)]
SkillUpload = Annotated[
    Upload, _capped(lambda u: max(u.skill_max_bytes, u.skill_archive_max_bytes))
]
AttachmentUpload = Annotated[Upload, _capped(lambda u: u.attachment_max_bytes)]
