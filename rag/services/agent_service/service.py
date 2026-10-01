from collections.abc import Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel

from rag.domain.agents import AgentSpec, Tool, ToolAgentSpec, ToolPort
from rag.domain.constants import LLM_RETRY_ATTEMPTS
from rag.domain.prompts import FALLBACK_MESSAGE
from rag.domain.resilience import or_default
from rag.services.agent_service.agent import Agent
from rag.services.agent_service.graphs.tool_agent import build_tool_agent


class AgentService:
    """The only holder of the LLM, and the only place LangChain is used: single-shot
    generation, and the tools and agents built on the model.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig],
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
        """One-shot completion enforced to fit `schema` (a Pydantic model class)"""
        llm = self._llm.with_structured_output(schema).with_retry(
            stop_after_attempt=attempts
        )
        return cast(T, await llm.ainvoke(prompt))

    def create_tools(self, tools: list[Tool]) -> list[ToolPort]:
        """Each tool, ready for an agent; raises ValueError if two share a name, which
        LangChain would otherwise only trip over once the agent runs.
        """
        names = [tool.name for tool in tools]
        if duplicates := sorted({name for name in names if names.count(name) > 1}):
            raise ValueError(f"tool names must be unique: {', '.join(duplicates)}")

        return [to_langchain_tool(tool) for tool in tools]

    def create_agent(self, spec: AgentSpec) -> Agent:
        """A chat agent built as `spec` describes. A new kind of agent adds its spec
        to AgentSpec, a graph builder in graphs/, and a case here.
        """
        match spec:
            case ToolAgentSpec():
                graph = build_tool_agent(
                    self._llm, spec, self._classify, self._checkpointer
                )
        return Agent(graph, self._trace_config)

    async def _classify(self, prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate(prompt, attempts=LLM_RETRY_ATTEMPTS), FALLBACK_MESSAGE
        )


def to_langchain_tool(tool: Tool) -> BaseTool:
    """The model reads the result's content; its references ride along as the
    ToolMessage's artifact, where the turn's references are collected from.
    """

    async def run(query: str) -> tuple[str, list[str] | None]:
        result = await tool.run(query)
        return result.content, result.references

    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=tool.description,
        response_format="content_and_artifact",
    )
