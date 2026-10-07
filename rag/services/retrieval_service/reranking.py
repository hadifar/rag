from pydantic import BaseModel, Field

from rag.domain.models import Chunk
from rag.domain.ports import LLMPort
from rag.services.retrieval_service.prompts import RERANK_PROMPT


class PassageVerdict(BaseModel):
    index: int = Field(description="The passage's index, as shown in brackets.")
    relevant: bool = Field(description="Whether it could help answer the question.")


class RerankOutput(BaseModel):
    verdicts: list[PassageVerdict]


class NoReranker:
    """RerankerPort that keeps the search's own order and scores."""

    async def rerank(
        self, query: str, candidates: list[tuple[Chunk, float]]
    ) -> list[tuple[Chunk, float]]:
        return candidates


class LlmReranker:
    """RerankerPort that has the LLM judge every candidate's summary relevant or not in
    one call, then keeps the relevant ones in the search's order, with their search
    scores; a candidate it gives no verdict on is dropped. Raises if the call fails.
    """

    def __init__(self, llm: LLMPort):
        self._llm = llm

    async def rerank(
        self, query: str, candidates: list[tuple[Chunk, float]]
    ) -> list[tuple[Chunk, float]]:
        if not candidates:
            return candidates

        passages = "\n".join(
            f"[{i}] {chunk.metadata.get('summary', '')}"
            for i, (chunk, _score) in enumerate(candidates)
        )
        prompt = RERANK_PROMPT.format(query=query, passages=passages)
        rerank_output = await self._llm.generate_structured(prompt, RerankOutput)

        relevant = {v.index for v in rerank_output.verdicts if v.relevant}
        return [c for i, c in enumerate(candidates) if i in relevant]
