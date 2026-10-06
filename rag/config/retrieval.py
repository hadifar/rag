from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    # retrieval score = (1 - summary_weight) * embedding_score + summary_weight * summary_score
    SUMMARY_WEIGHT: float = Field(default=0.5, ge=0, le=1)
    # Passages the knowledge-base search fetches.
    RETRIEVAL_CANDIDATES: int = Field(default=10, ge=1)
    # Passages the LLM reranker keeps of those; 0 turns reranking off.
    RERANK_CANDIDATES: int = Field(default=3, ge=0)

    @property
    def top_k(self) -> int:
        """Passages a search returns: the reranker's pick, or every fetched one."""
        return self.RERANK_CANDIDATES or self.RETRIEVAL_CANDIDATES
