from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    # Share of a passage's search score from its document's summary (title,
    # description, headings); the rest comes from the passage text itself.
    SUMMARY_WEIGHT: float = Field(default=0.5, ge=0, le=1)
    # Has the LLM score each found passage's summary (1-10) and reorders them by it.
    RERANK: bool = True
