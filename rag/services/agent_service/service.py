import uuid
from collections.abc import AsyncIterator, Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from pydantic import BaseModel

from rag.domain.errors import PreferenceNotFoundError
from rag.domain.models import (
    AgentSpec,
    HistoryMessage,
    Preference,
    ReferencesReady,
    StreamEvent,
    ToolAgentSpec,
)
from rag.services.agent_service.graphs.agent_builder import build_tool_agent
from rag.services.agent_service.middleware import preferences
from rag.services.agent_service.middleware.preferences import ChatContext
from rag.services.agent_service.prompts import FALLBACK_MESSAGE
from rag.services.agent_service.streaming import parse_event
from rag.services.agent_service.turn import to_history, turn_references
from rag.shared.resilience import or_default

# TODO: error hanlding -> Something went wrong: Unexpected end of JSON input

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip plus the guards' and retry middleware's nodes cost several steps.
RECURSION_LIMIT = 75


class Agent:
    """A chat agent on any message-state graph: streams each turn's events, then what its
    tools cited. The graph saves the turn's messages through its checkpointer; the agent
    service reads them back (`AgentService.get_history`).
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        trace_config: Callable[[str | None], RunnableConfig],
    ):
        self._graph = graph
        self._trace_config = trace_config

    def _config(self, thread_id: str) -> RunnableConfig:
        return {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": RECURSION_LIMIT,
            **self._trace_config("chat"),
        }

    async def stream(
        self, message: str, thread_id: str, user_id: uuid.UUID
    ) -> AsyncIterator[StreamEvent]:
        config = self._config(thread_id)

        async for raw_event in self._graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            context=ChatContext(user_id=user_id),
            version="v2",
        ):
            for event in parse_event(raw_event):
                yield event

        final_state = await self._graph.aget_state(config)
        references = turn_references(final_state.values.get("messages", []))
        if references is not None:
            yield ReferencesReady(references=references)


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

    async def get_preferences(self, user_id: uuid.UUID) -> list[Preference]:
        """What the user wants of every answer, oldest first."""
        return await preferences.list_preferences(self._store, user_id)

    async def add_preference(self, user_id: uuid.UUID, text: str) -> Preference:
        """The saved preference, or the same one if the user already has it. Raises
        InvalidPreferenceError or TooManyPreferencesError.
        """
        return await preferences.save_preference(self._store, user_id, text)

    async def delete_preference(self, user_id: uuid.UUID, preference_id: str) -> None:
        """Raises PreferenceNotFoundError if the user has no preference with that id."""
        if not await preferences.delete_preference(self._store, user_id, preference_id):
            raise PreferenceNotFoundError(preference_id)

    async def _classify(self, prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate(prompt, attempts=self._retry_attempts), FALLBACK_MESSAGE
        )
