from fastapi import APIRouter, Depends

from rag.api.deps import get_current_user
from rag.api.schema.settings import SettingsResponse

router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings() -> SettingsResponse:
    return SettingsResponse.reported()
