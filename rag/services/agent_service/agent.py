import logging
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.schema import StreamEvent as RawEvent
from langgraph.graph.state import CompiledStateGraph

from rag.domain.models import (
    AgentMemory,
    ArtifactsReady,
    RunContext,
    StreamEvent,
    TurnFailed,
)
from rag.services.agent_service.prompts import TURN_FAILED_MESSAGE
from rag.services.agent_service.streaming import AnswerGate, parse_event
from rag.services.agent_service.turn import turn_artifacts

logger = logging.getLogger(__name__)

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip plus the guards' and retry middleware's nodes cost several steps.
RECURSION_LIMIT = 75


class Agent:
    """A chat agent on any message-state graph. It keeps nothing between turns: each
    turn is given the agent's memory of the earlier ones, and hands back its own
    (see `AgentTurn`); what the user saw is the chat service's to keep.
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        trace_config: Callable[[str | None, RunContext | None], RunnableConfig],
    ):
        self._graph = graph
        self._trace_config = trace_config

    def stream(
        self, message: str, history: Sequence[AgentMemory], ctx: RunContext
    ) -> "AgentTurn":
        config: RunnableConfig = {
            "recursion_limit": RECURSION_LIMIT,
            **self._trace_config("chat", ctx),
        }
        return AgentTurn(self._graph, config, message, history, ctx)


class AgentTurn:
    """One turn: iterate it for its events, then what its tools handed the user. Once
    they end, `memory` holds the turn's messages, from the question on; it stays None
    for a turn to forget: a blocked question, a failed tool or model call (whose
    unanswered tool call the model's API would reject in every later turn), or a
    stream its caller stopped reading.
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        config: RunnableConfig,
        message: str,
        history: Sequence[AgentMemory],
        ctx: RunContext,
    ):
        self._graph = graph
        self._config = config
        self._question = HumanMessage(content=message, id=str(uuid.uuid4()))
        self._history = [m for turn in history for m in messages_from_dict(turn)]
        self._ctx = ctx
        self.memory: AgentMemory | None = None

    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        """If a tool or the model fails, the turn ends with `TurnFailed` instead."""
        try:
            final_state: dict[str, Any] = {}
            async for event in self._turn_events(final_state):
                yield event

            messages: list[BaseMessage] = final_state.get("messages", [])
            ids = [m.id for m in messages]
            # A blocked question is dropped from the state, and with it its turn.
            if self._question.id not in ids:
                return
            turn = messages[ids.index(self._question.id) :]
            self.memory = messages_to_dict(turn)
            artifacts = turn_artifacts(turn)
            if artifacts is not None:
                yield ArtifactsReady(artifacts=artifacts)

        except Exception:
            logger.exception("chat turn failed")
            self.memory = None
            yield TurnFailed(message=TURN_FAILED_MESSAGE)

    async def _turn_events(
        self, final_state: dict[str, Any]
    ) -> AsyncIterator[StreamEvent]:
        """The turn's events as the user is to see them: an answer the groundedness
        guard checks is held back until its verdict (see `AnswerGate`). Fills
        `final_state` with the graph's state once the run ends.
        """
        gate = AnswerGate()
        async for raw_event in self._graph.astream_events(
            {"messages": [*self._history, self._question]},
            config=self._config,
            context=self._ctx,
            version="v2",
        ):
            final_state.update(_final_state(raw_event))
            for event in parse_event(raw_event):
                for released in gate.feed(event):
                    yield released
        for released in gate.flush():
            yield released


def _final_state(raw_event: RawEvent) -> dict[str, Any]:
    """The graph's final state if `raw_event` is the run's own end (it has no parent);
    else nothing.
    """
    if raw_event["event"] != "on_chain_end" or raw_event["parent_ids"]:
        return {}
    return raw_event["data"].get("output") or {}
