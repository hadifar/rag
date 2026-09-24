from fastapi import APIRouter

from rag.api.schema import SettingsResponse
from rag.config import Settings
from rag.services.generation_service.graph import SYSTEM_PROMPT

# Static for now — not yet threaded through the generation/ranking calls they name.
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_K = 4


def build_settings_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["settings"])

    @router.get("")
    async def get_settings() -> SettingsResponse:
        return SettingsResponse(
            model=settings.OPENAI_MODEL,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
            system_prompt=SYSTEM_PROMPT,
        )

    return router
