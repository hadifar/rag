import uuid
from datetime import datetime

from pydantic import BaseModel

from rag.domain.models import IngestionRun, IngestionRunStatus


class IngestionRunResponse(BaseModel):
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

    @classmethod
    def from_domain(cls, run: IngestionRun) -> "IngestionRunResponse":
        return cls(
            id=run.id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            added=run.added,
            updated=run.updated,
            unchanged=run.unchanged,
            removed=run.removed,
            error=run.error,
        )
