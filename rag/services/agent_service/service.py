from collections.abc import Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel

from rag.domain.constants import LLM_RETRY_ATTEMPTS
from rag.domain.ports import SearchPort, ToolPort
from rag.domain.prompts import FALLBACK_MESSAGE
from rag.domain.resilience import or_default
from rag.services.agent_service.agents.rag_agent import RagAgent, build_graph
from rag.services.agent_service.tools import build_search_tool


def _no_trace(name: str | None = None) -> RunnableConfig:
    return {}


class AgentService:
    """The only holder of the LLM, and the only place LangChain is used: single-shot
    generation, and the tools and agents built on the model.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig] = _no_trace,
    ):
        self._llm = llm
        self._checkpointer = checkpointer
        self._trace_config = trace_config

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        llm = self._llm.with_retry(stop_after_attempt=attempts)
        return (await llm.ainvoke(prompt)).text

    async def generate_structured[T: BaseModel](
        self, prompt: str, schema: type[T], *, attempts: int = 1
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), as an
        instance of it; raises if all `attempts` fail or the reply is rejected.
        """
        llm = self._llm.with_structured_output(schema).with_retry(
            stop_after_attempt=attempts
        )
        return cast(T, await llm.ainvoke(prompt))

    def create_tool(self, knowledge_base: SearchPort) -> ToolPort:
        """search_kb: the agent's search of `knowledge_base`."""
        return build_search_tool(knowledge_base)

    def create_rag_agent(self, tools: list[ToolPort]) -> RagAgent:
        """The guarded chat agent, answering with `tools` (from `create_tool`)."""
        graph = build_graph(
            self._llm,
            self._classify,
            cast(list[BaseTool], tools),  # only this service builds them
            self._checkpointer,
        )
        return RagAgent(graph, self._trace_config)

    async def _classify(self, prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate(prompt, attempts=LLM_RETRY_ATTEMPTS), FALLBACK_MESSAGE
        )
