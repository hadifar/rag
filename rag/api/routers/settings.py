from fastapi import APIRouter

from rag.api.schema import SettingsResponse
from rag.config import Settings

# TODO: later change default model
# Static for now
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_K = 4
DEFAULT_MODEL = "gpt-4o-mini"


def build_settings_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["settings"])

    @router.get("")
    async def get_settings() -> SettingsResponse:

        return SettingsResponse(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
        )

    return router
