from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    # retrieval score = (1 - summary_weight) * embedding_score + summary_weight * summary_score
    SUMMARY_WEIGHT: float = Field(default=0.5, ge=0, le=1)
    RERANK: bool = True
    # Passages the search hands the reranker, which keeps the best RAG__TOP_K of them.
    RERANK_CANDIDATES: int = Field(default=30, ge=1)
