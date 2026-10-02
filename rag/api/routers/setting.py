from fastapi import APIRouter, Depends

from rag.api.deps import (
    AuthenticatedUserDep,
    PreferenceServiceDep,
    SettingsDep,
    get_current_user,
)
from rag.api.schema.setting import (
    PreferenceRequest,
    PreferenceResponse,
    SettingsResponse,
)

# Settings: the app's, read from its configuration, and the caller's own preferences.
router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings(settings: SettingsDep) -> SettingsResponse:
    return SettingsResponse.from_settings(settings)


@router.get("/preferences")
async def list_preferences(
    current_user: AuthenticatedUserDep, preference_service: PreferenceServiceDep
) -> list[PreferenceResponse]:
    """What the caller wants of every answer, oldest first; the chat agent applies
    them, and saves or forgets them when asked to in a conversation too.
    """
    preferences = await preference_service.list_for_user(current_user.id)
    return [PreferenceResponse.model_validate(p) for p in preferences]


@router.post("/preferences")
async def add_preference(
    preference_request: PreferenceRequest,
    current_user: AuthenticatedUserDep,
    preference_service: PreferenceServiceDep,
) -> PreferenceResponse:
    """Saves the preference; one the caller already has (ignoring case) comes back
    as it is. 409 once they have the most allowed.
    """
    preference = await preference_service.add(current_user.id, preference_request.text)
    return PreferenceResponse.model_validate(preference)


@router.delete("/preferences/{preference_id}", status_code=204)
async def delete_preference(
    preference_id: str,
    current_user: AuthenticatedUserDep,
    preference_service: PreferenceServiceDep,
) -> None:
    await preference_service.delete(current_user.id, preference_id)
