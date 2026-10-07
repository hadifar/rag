import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Skill:
    """Instructions a user saved for the agent: it sees every skill's `name` and
    `description`, and loads a skill's instructions when a request fits it.
    """

    id: uuid.UUID
    name: str  # unique per user: lowercase letters, digits and hyphens
    description: str  # when the agent is to use it
    created_at: datetime
    updated_at: datetime  # when it was last uploaded (again)
