from pydantic import BaseModel, Field

from rag.domain.ports import AgentServicePort
from rag.shared.resilience import or_default

EXPAND_PROMPT = (
    "Rewrite the search query below in {count} different ways, to find passages in "
    "a product's documentation that the original wording might miss. Keep the same "
    "meaning; vary the words: use synonyms, the terms the documentation would use, "
    "and a more specific or more general phrasing.\n\n"
    "QUERY:\n{query}"
)


class ExpandOutput(BaseModel):
    queries: list[str] = Field(description="The rewritten queries.")


class NoQueryExpander:
    """QueryExpanderPort that adds no phrasings: the search runs the query alone."""

    async def expand(self, query: str) -> list[str]:
        return []


class LlmQueryExpander:
    """QueryExpanderPort that has the LLM rewrite the query `count` ways in one call.
    Blank and repeated phrasings, and the query itself, are dropped. If the call
    fails, there are none.
    """

    def __init__(self, agent_service: AgentServicePort, count: int, attempts: int):
        self._agent_service = agent_service
        self._count = count
        self._attempts = attempts

    async def expand(self, query: str) -> list[str]:
        prompt = EXPAND_PROMPT.format(count=self._count, query=query)
        reply = await or_default(
            self._agent_service.generate_structured(
                prompt, ExpandOutput, attempts=self._attempts
            ),
            None,
        )
        if reply is None:
            return []

        seen = {query.strip().casefold()}
        variants: list[str] = []
        for variant in (q.strip() for q in reply.queries):
            if variant and variant.casefold() not in seen:
                seen.add(variant.casefold())
                variants.append(variant)
        return variants[: self._count]
