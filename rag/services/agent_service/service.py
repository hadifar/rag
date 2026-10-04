import uuid
from collections.abc import AsyncIterator, Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from rag.domain.models import (
    AgentSpec,
    ReferencesReady,
    RunContext,
    StreamEvent,
    ToolAgentSpec,
)
from rag.services.agent_service.graphs.agent_builder import build_tool_agent
from rag.services.agent_service.prompts import FALLBACK_MESSAGE
from rag.services.agent_service.streaming import AnswerGate, parse_event
from rag.services.agent_service.turn import turn_references
from rag.shared.resilience import or_default

# TODO: error hanlding -> Something went wrong: Unexpected end of JSON input

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip plus the guards' and retry middleware's nodes cost several steps.
RECURSION_LIMIT = 75


class Agent:
    """A chat agent on any message-state graph: streams each turn's events, then what its
    tools cited. The graph keeps each conversation's messages, the model's memory of it,
    through its checkpointer; what the user saw is the conversation service's to keep.
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig],
    ):
        self._graph = graph
        self._checkpointer = checkpointer
        self._trace_config = trace_config

    def _config(self, thread_id: str) -> RunnableConfig:
        return {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": RECURSION_LIMIT,
            **self._trace_config("chat"),
        }

    async def stream(self, message: str, ctx: RunContext) -> AsyncIterator[StreamEvent]:
        config = self._config(str(ctx.conversation_id))

        async for event in self._turn_events(message, ctx, config):
            yield event

        final_state = await self._graph.aget_state(config)
        references = turn_references(final_state.values.get("messages", []))
        if references is not None:
            yield ReferencesReady(references=references)

    async def _turn_events(
        self, message: str, ctx: RunContext, config: RunnableConfig
    ) -> AsyncIterator[StreamEvent]:
        """The turn's events as the user is to see them: an answer the groundedness
        guard checks is held back until its verdict (see `AnswerGate`).
        """
        gate = AnswerGate()
        async for raw_event in self._graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            context=ctx,
            version="v2",
        ):
            for event in parse_event(raw_event):
                for released in gate.feed(event):
                    yield released
        for released in gate.flush():
            yield released

    async def forget(self, conversation_id: uuid.UUID) -> None:
        await self._checkpointer.adelete_thread(str(conversation_id))


class AgentService:
    """The only holder of the LLM, and the only place LangChain is used: single-shot
    generation, and the agents built on the model.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        trace_config: Callable[[str | None], RunnableConfig],
        retry_attempts: int,  # tries per LLM call in agents and guards before falling back
    ):
        self._llm = llm
        self._checkpointer = checkpointer
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
                    self._retry_attempts,
                )
        return Agent(graph, self._checkpointer, self._trace_config)

    async def _classify(self, prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate(prompt, attempts=self._retry_attempts), FALLBACK_MESSAGE
        )
