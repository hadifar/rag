from fastapi import APIRouter, Depends

from rag.api.deps import AppSettingsDep, get_current_user
from rag.api.schema.setting import SettingsResponse

# Settings: the app's, read from its configuration.
router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings(app_settings: AppSettingsDep) -> SettingsResponse:
    return SettingsResponse.model_validate(app_settings)
