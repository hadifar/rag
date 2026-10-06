from fastapi import APIRouter, Depends

from rag.api.deps import RetrievalServiceDep, SettingsDep, get_current_user
from rag.api.schema.setting import SettingsResponse

# Settings: the app's, read from its configuration.
router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_settings(
    settings: SettingsDep, retrieval_service: RetrievalServiceDep
) -> SettingsResponse:
    # top_k is the search's: the reranker's pick, or every fetched passage.
    return SettingsResponse.from_settings(settings, top_k=retrieval_service.top_k)
