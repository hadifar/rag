import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from rag.domain.models import (
    ReferencesReady,
    RunContext,
    StreamEvent,
    ToolAgentSpec,
    TurnFailed,
)
from rag.services.agent_service.agent_builder import build_tool_agent
from rag.services.agent_service.prompts import FALLBACK_MESSAGE, TURN_FAILED_MESSAGE
from rag.services.agent_service.streaming import AnswerGate, parse_event
from rag.services.agent_service.turn import turn_references
from rag.shared.resilience import or_default

logger = logging.getLogger(__name__)

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
        trace_config: Callable[[str | None, RunContext | None], RunnableConfig],
    ):
        self._graph = graph
        self._checkpointer = checkpointer
        self._trace_config = trace_config

    def _config(self, ctx: RunContext) -> RunnableConfig:
        return {
            "configurable": {"thread_id": str(ctx.conversation_id)},
            "recursion_limit": RECURSION_LIMIT,
            **self._trace_config("chat", ctx),
        }

    async def stream(self, message: str, ctx: RunContext) -> AsyncIterator[StreamEvent]:
        """The turn's events. If a tool or the model fails, the turn ends with
        `TurnFailed` instead, and the thread forgets it, so the same message can be
        sent again.
        """
        config = self._config(ctx)
        question = HumanMessage(content=message, id=str(uuid.uuid4()))

        try:
            async for event in self._turn_events(question, ctx, config):
                yield event

            final_state = await self._graph.aget_state(config)
            references = turn_references(final_state.values.get("messages", []))
            if references is not None:
                yield ReferencesReady(references=references)
        except Exception:
            logger.exception("chat turn failed")
            await self._forget_turn(question, config)
            yield TurnFailed(message=TURN_FAILED_MESSAGE)

    async def _forget_turn(
        self, question: HumanMessage, config: RunnableConfig
    ) -> None:
        """Removes `question` and everything after it from the thread. A failed tool
        call leaves the model's request for it unanswered, which the model's API
        rejects in every later turn. The list is replaced whole rather than removed by
        id: the state also shows the results of tools that finished alongside the
        failed one, which were never saved, and removing those ids would fail.
        """
        try:
            messages = (await self._graph.aget_state(config)).values.get("messages", [])
            ids = [m.id for m in messages]
            if question.id not in ids:
                return
            kept = messages[: ids.index(question.id)]
            await self._graph.aupdate_state(
                config,
                {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *kept]},
            )
        except Exception:
            logger.exception("couldn't forget the failed chat turn")

    async def _turn_events(
        self, question: HumanMessage, ctx: RunContext, config: RunnableConfig
    ) -> AsyncIterator[StreamEvent]:
        """The turn's events as the user is to see them: an answer the groundedness
        guard checks is held back until its verdict (see `AnswerGate`).
        """
        gate = AnswerGate()
        async for raw_event in self._graph.astream_events(
            {"messages": [question]},
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
        trace_config: Callable[[str | None, RunContext | None], RunnableConfig],
        retry_attempts: int,  # tries per LLM call before an agent's turn fails or a guard falls back
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
        self,
        prompt: str,
        schema: type[T],
        *,
        attempts: int = 1,
        trace: str | None = None,
        ctx: RunContext | None = None,
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class)"""
        llm = self._llm.with_structured_output(schema).with_retry(
            stop_after_attempt=attempts
        )
        # Its own trace only if named: inside an agent's run, a config of its own would
        # cut the call from the run's trace.
        config = self._trace_config(trace, ctx) if trace is not None else None
        return cast(T, await llm.ainvoke(prompt, config=config))

    def create_agent(self, spec: ToolAgentSpec) -> Agent:
        """A chat agent built as `spec` describes; raises ValueError if two of its
        tools share a name.
        """
        graph = build_tool_agent(
            self._llm, spec, self._classify, self._checkpointer, self._retry_attempts
        )
        return Agent(graph, self._checkpointer, self._trace_config)

    async def _classify(self, prompt: str) -> str:
        """The guards' LLM call: retried, and if it still fails, answers with the
        fallback message, which neither guard reads as a rejection (they fail open).
        """
        return await or_default(
            self.generate(prompt, attempts=self._retry_attempts), FALLBACK_MESSAGE
        )
