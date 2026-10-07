import uuid
from dataclasses import dataclass
from datetime import datetime

# What a skill's name may be: lowercase letters and digits, in hyphen-joined words.
# The user_skills.name check (migration 0021) spells it too.
SKILL_NAME_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"


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
