from collections.abc import Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore
from pydantic import BaseModel

from rag.domain.models import AgentSpec, HistoryMessage, ToolAgentSpec
from rag.services.agent_service.agent import Agent
from rag.services.agent_service.graphs.tool_agent import build_tool_agent
from rag.services.agent_service.prompts import FALLBACK_MESSAGE
from rag.services.agent_service.turn import to_history
from rag.shared.resilience import or_default


class AgentService:
    """The only holder of the LLM, and the only place LangChain is used: single-shot
    generation, the tools and agents built on the model, and the threads they save.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        store: BaseStore,
        trace_config: Callable[[str | None], RunnableConfig],
        retry_attempts: int,  # tries per LLM call in agents and guards before falling back
    ):
        self._llm = llm
        self._checkpointer = checkpointer
        self._store = store
        self._trace_config = trace_config
        self._retry_attempts = retry_attempts

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        llm = self._llm.with_retry(stop_after_attempt=attempts)
        return (await llm.ainvoke(prompt)).text

    async def generate_structured[T: BaseModel](
        self, prompt: str, schema: type[T], *, attempts: int = 1
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class)"""
        llm = self._llm.with_structured_output(schema).with_retry(
            stop_after_attempt=attempts
        )
        return cast(T, await llm.ainvoke(prompt))

    def create_agent(self, spec: AgentSpec) -> Agent:
        """A chat agent built as `spec` describes; raises ValueError if two of its
        tools share a name. A new kind of agent adds its spec to AgentSpec, a graph
        builder in graphs/, and a case here.
        """
        match spec:
            case ToolAgentSpec():
                graph = build_tool_agent(
                    self._llm,
                    spec,
                    self._classify,
                    self._checkpointer,
                    self._store,
                    self._retry_attempts,
                )
        return Agent(graph, self._trace_config)

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        """The thread's messages as the user saw them; empty for an unknown thread."""
        checkpoint = await self._checkpointer.aget(
            {"configurable": {"thread_id": thread_id}}
        )
        messages: list[BaseMessage] = (
            checkpoint["channel_values"].get("messages", []) if checkpoint else []
        )
        return to_history(messages)

    async def delete_history(self, thread_id: str) -> None:
        await self._checkpointer.adelete_thread(thread_id)

    async def _classify(self, prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate(prompt, attempts=self._retry_attempts), FALLBACK_MESSAGE
        )
