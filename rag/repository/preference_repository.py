import uuid

from psycopg.errors import CheckViolation

from rag.domain.errors import TooManyPreferencesError
from rag.domain.models import MAX_PREFERENCES, Preference
from rag.repository.base_repository import BaseRepository

_COLUMNS = "id, text"


class PreferenceRepository(BaseRepository[Preference]):
    row_type = Preference

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        return await self._fetch_all(
            f"SELECT {_COLUMNS} FROM user_preferences "
            "WHERE user_id = %s ORDER BY created_at, id",
            (user_id,),
        )

    async def add(self, user_id: uuid.UUID, preference: Preference) -> Preference:
        try:
            added = await self._fetch_one(
                f"""
                INSERT INTO user_preferences (id, user_id, text) VALUES (%s, %s, %s)
                ON CONFLICT (user_id, lower(text)) DO NOTHING
                RETURNING {_COLUMNS}
                """,
                (preference.id, user_id, preference.text),
            )
        except CheckViolation as exc:  # tr_user_preferences_cap
            if exc.diag.constraint_name == "ck_user_preferences_cap":
                raise TooManyPreferencesError(MAX_PREFERENCES) from exc
            raise
        if added is not None:
            return added
        # Lost a race to the same text: that one is what the user has.
        existing = await self._fetch_one(
            f"SELECT {_COLUMNS} FROM user_preferences "
            "WHERE user_id = %s AND lower(text) = lower(%s)",
            (user_id, preference.text),
        )
        assert existing is not None  # the conflicting row; preferences aren't edited
        return existing

    async def delete(self, user_id: uuid.UUID, preference_id: str) -> bool:
        deleted = await self._execute(
            "DELETE FROM user_preferences WHERE user_id = %s AND id = %s",
            (user_id, preference_id),
        )
        return deleted > 0
