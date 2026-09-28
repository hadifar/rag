import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from rag.domain.models import IngestionRunStatus


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: IngestionRunStatus
    started_at: datetime
    finished_at: datetime | None
    # Set once the run succeeded.
    added: int | None
    updated: int | None
    unchanged: int | None
    removed: int | None
    # Set once the run failed.
    error: str | None
