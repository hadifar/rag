from pydantic import BaseModel


class SettingsResponse(BaseModel):
    model: str
    temperature: float
    top_k: int
