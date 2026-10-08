import uuid

from rag.domain.errors import UserNotFoundError
from rag.domain.models import AppSettings, RunSettingsUpdate, User
from rag.domain.ports import UserRepositoryPort


class SettingService:
    """Settings: the app's (`app`), fixed by its configuration; and each user's own,
    the model and effort their chat turns run on, one pick for all their
    conversations, kept on the user.
    """

    def __init__(self, app: AppSettings, users: UserRepositoryPort):
        self._app = app
        self._users = users

    @property
    def app(self) -> AppSettings:
        return self._app

    async def get_run_settings(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def update_run_settings(
        self, user_id: uuid.UUID, change: RunSettingsUpdate
    ) -> User:
        """A field `change` leaves None stays as is."""
        user = await self._users.update_run_settings(user_id, change)
        if user is None:
            raise UserNotFoundError(user_id)
        return user
