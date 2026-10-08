import uuid

from rag.domain.errors import UserNotFoundError
from rag.domain.models import RunSettingsUpdate, User
from rag.domain.ports import UserRepositoryPort


class RunSettingsService:
    """The model and effort a user's chat turns run on: one pick for all their
    conversations, kept on the user.
    """

    def __init__(self, users: UserRepositoryPort):
        self._users = users

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def update(self, user_id: uuid.UUID, change: RunSettingsUpdate) -> User:
        """A field `change` leaves None stays as is."""
        user = await self._users.update_run_settings(user_id, change)
        if user is None:
            raise UserNotFoundError(user_id)
        return user
