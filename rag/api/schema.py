from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str
    message: str = Field(min_length=1, max_length=8196)


class SettingsResponse(BaseModel):
    model: str
    temperature: float
    top_k: int


class HealthResponse(BaseModel):
    status: str
