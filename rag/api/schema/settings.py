from pydantic import BaseModel

from rag.domain.constants import REPORTED_MODEL, REPORTED_TEMPERATURE, SEARCH_TOP_K


class SettingsResponse(BaseModel):
    model: str
    temperature: float
    top_k: int

    @classmethod
    def reported(cls) -> "SettingsResponse":
        return cls(
            model=REPORTED_MODEL, temperature=REPORTED_TEMPERATURE, top_k=SEARCH_TOP_K
        )
