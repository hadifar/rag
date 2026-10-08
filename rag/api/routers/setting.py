from fastapi import APIRouter, Depends

from rag.api.deps import (
    AuthenticatedUserDep,
    SettingServiceDep,
    get_current_user,
)
from rag.api.schema.setting import (
    RunSettingsResponse,
    RunSettingsUpdateRequest,
    SettingsResponse,
)

# Settings: the app's, read from its configuration; and the user's own.
router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings(settings: SettingServiceDep) -> SettingsResponse:
    return SettingsResponse.model_validate(settings.app)


@router.get("/me")
async def get_run_settings(
    current_user: AuthenticatedUserDep, settings: SettingServiceDep
) -> RunSettingsResponse:
    """The model and effort the user's turns run on, in every conversation."""
    user = await settings.get_run_settings(current_user.id)
    return RunSettingsResponse.model_validate(user)


@router.patch("/me")
async def update_run_settings(
    request: RunSettingsUpdateRequest,
    current_user: AuthenticatedUserDep,
    settings: SettingServiceDep,
) -> RunSettingsResponse:
    """Sets the model or effort the user's turns run on, in every conversation."""
    user = await settings.update_run_settings(current_user.id, request.to_update())
    return RunSettingsResponse.model_validate(user)
