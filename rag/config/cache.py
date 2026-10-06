from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Caches, in Postgres, of what the same input always gives: a query's embedding,
    a search's reranked result (emptied by every ingestion) and the off-topic guard's
    verdict. Each entry is keyed by the model that made it, so a new model misses.
    """

    # Off: every embedding, search and verdict is computed afresh.
    ENABLED: bool = True
    EMBEDDING_TTL_DAYS: int = Field(default=7, ge=1)
    SEARCH_TTL_DAYS: int = Field(default=7, ge=1)
    VERDICT_TTL_DAYS: int = Field(default=7, ge=1)
