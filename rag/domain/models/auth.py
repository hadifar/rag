import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    created_at: datetime
    # Admins can replace the knowledge base; granted out-of-band (`rag set-admin`).
    is_admin: bool = False
