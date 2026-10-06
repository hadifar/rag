from fastapi import APIRouter, Depends

from rag.api.deps import SettingsDep, get_current_user
from rag.api.schema.setting import SettingsResponse

# Settings: the app's, read from its configuration.
router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings(settings: SettingsDep) -> SettingsResponse:
    return SettingsResponse.from_settings(settings)
