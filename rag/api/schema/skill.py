import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SkillResponse(BaseModel):
    """A skill the user saved; the agent loads its instructions when a request fits its
    description.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
