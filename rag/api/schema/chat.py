from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str
    message: str = Field(min_length=1, max_length=8196)
