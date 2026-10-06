from pydantic import BaseModel, Field

from rag.domain.models import Chunk
from rag.domain.ports import LLMServicePort
from rag.services.retrieval_service.prompts import RERANK_PROMPT
from rag.shared.resilience import or_default

MIN_SCORE, MAX_SCORE = 1, 10
UNSCORED = 0
MIN_CANDIDATES = 2


class PassageScore(BaseModel):
    index: int = Field(description="The passage's index, as shown in brackets.")
    score: int = Field(description=f"From {MIN_SCORE} to {MAX_SCORE}.")


class RerankOutput(BaseModel):
    scores: list[PassageScore]


class NoReranker:
    """RerankerPort that keeps the search's own order and scores."""

    async def rerank(
        self, query: str, candidates: list[tuple[Chunk, float]]
    ) -> list[tuple[Chunk, float]]:
        return candidates


class LlmReranker:
    """RerankerPort that has the LLM score every candidate's summary in one call, then
    orders them by that score; ties keep the search's order. If the call fails, the
    candidates come back as given.
    """

    def __init__(self, llm_service: LLMServicePort, attempts: int):
        self._llm_service = llm_service
        self._attempts = attempts

    async def rerank(
        self, query: str, candidates: list[tuple[Chunk, float]]
    ) -> list[tuple[Chunk, float]]:
        if len(candidates) < MIN_CANDIDATES:
            return candidates

        passages = "\n".join(
            f"[{i}] {chunk.metadata.get('summary', '')}"
            for i, (chunk, _score) in enumerate(candidates)
        )
        prompt = RERANK_PROMPT.format(query=query, passages=passages)
        reply = await or_default(
            self._llm_service.generate_structured(
                prompt, RerankOutput, attempts=self._attempts
            ),
            None,
        )
        if reply is None:
            return candidates

        scores = {
            s.index: min(max(s.score, MIN_SCORE), MAX_SCORE)
            for s in reply.scores
            if 0 <= s.index < len(candidates)
        }
        order = sorted(range(len(candidates)), key=lambda i: -scores.get(i, UNSCORED))
        return [(candidates[i][0], float(scores.get(i, UNSCORED))) for i in order]
