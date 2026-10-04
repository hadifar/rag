from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    # Share of a passage's search score from its document's summary (title,
    # description, headings); the rest comes from the passage text itself.
    SUMMARY_WEIGHT: float = Field(default=0.5, ge=0, le=1)
