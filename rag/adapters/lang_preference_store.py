import uuid

from langgraph.store.base import BaseStore

from rag.domain.models import MAX_PREFERENCES, Preference


class LangGraphPreferenceRepository:
    """PreferenceRepositoryPort on LangGraph's store: one item per preference, under
    the user's own namespace, so a lookup can only ever reach their own.
    """

    def __init__(self, store: BaseStore):
        self._store = store

    async def list_for_user(self, user_id: uuid.UUID) -> list[Preference]:
        items = await self._store.asearch(_namespace(user_id), limit=MAX_PREFERENCES)
        return [
            Preference(id=item.key, text=item.value["text"])
            for item in sorted(items, key=lambda item: item.created_at)
        ]

    async def add(self, user_id: uuid.UUID, preference: Preference) -> None:
        await self._store.aput(
            _namespace(user_id), preference.id, {"text": preference.text}
        )

    async def delete(self, user_id: uuid.UUID, preference_id: str) -> bool:
        namespace = _namespace(user_id)
        if await self._store.aget(namespace, preference_id) is None:
            return False
        await self._store.adelete(namespace, preference_id)
        return True


def _namespace(user_id: uuid.UUID) -> tuple[str, ...]:
    return ("users", str(user_id), "preferences")
