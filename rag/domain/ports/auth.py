import uuid
from collections.abc import Mapping
from typing import Any, Protocol

from rag.domain.models import RunSettingsUpdate, User


class UserRepositoryPort(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def create(
        self, email: str, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        """Raises UserAlreadyExistsError if the email is taken."""
        ...

    async def set_admin(self, email: str, is_admin: bool) -> User | None:
        """None if no user has that email."""
        ...

    async def update_run_settings(
        self, user_id: uuid.UUID, change: RunSettingsUpdate
    ) -> User | None:
        """A field `change` leaves None stays as is. None if no user has that id."""
        ...


class PasswordHasherPort(Protocol):
    async def hash(self, password: str) -> str: ...

    async def verify(self, hashed_password: str, password: str) -> bool: ...


class TokenCodecPort(Protocol):
    def encode(self, claims: Mapping[str, Any]) -> str: ...

    def decode(self, token: str) -> dict[str, Any]:
        """Raises InvalidTokenError if the token is expired, malformed, or badly signed."""
        ...
