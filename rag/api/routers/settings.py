from fastapi import APIRouter, Depends

from rag.api.deps import get_current_user
from rag.api.schema.settings import SettingsResponse

# TODO: later change default model
# Static for now
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_K = 4
DEFAULT_MODEL = "gpt-4o-mini"

router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings() -> SettingsResponse:
    return SettingsResponse(
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        top_k=DEFAULT_TOP_K,
    )
