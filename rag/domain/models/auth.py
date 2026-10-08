import uuid
from dataclasses import dataclass
from datetime import datetime

from rag.domain.models.agent.agent import (
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    Effort,
    ModelName,
)


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    created_at: datetime
    # Admins can replace the knowledge base; granted out-of-band (`rag set-admin`).
    is_admin: bool = False
    # What their chat turns run on, in every conversation: the last they picked.
    model: ModelName = DEFAULT_MODEL
    effort: Effort = DEFAULT_EFFORT


@dataclass(frozen=True)
class RunSettingsUpdate:
    """What to change about the model and effort a user's turns run on; a field left
    None stays as is.
    """

    model: ModelName | None = None
    effort: Effort | None = None
