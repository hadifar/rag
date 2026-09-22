from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class SettingsResponse(BaseModel):
    model: str
    temperature: float
    top_k: int
    system_prompt: str
