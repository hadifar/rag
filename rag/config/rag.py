from pydantic import BaseModel, Field


class RagConfig(BaseModel):
    TOP_K: int = Field(default=10, ge=1)  # passages the knowledge-base search returns
    # Times the groundedness guard sends an answer back per turn; 0 only verifies.
    MAX_REVISIONS: int = Field(default=1, ge=0)
