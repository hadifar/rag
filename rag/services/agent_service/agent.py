import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal, NotRequired, cast

from langchain.agents.middleware.todo import (
    WRITE_TODOS_SYSTEM_PROMPT,
    Todo,
    write_todos,
)
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    messages_from_dict,
)
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, RetryPolicy

from rag.domain.models import (
    AgentMemory,
    InputDecision,
    InputVerdict,
    RunContext,
    StreamEvent,
    TurnFailed,
)
from rag.domain.ports import CachePort, SearchPort
from rag.services.agent_service.guards.groundedness import (
    is_grounded,
    verification_inputs,
)
from rag.services.agent_service.guards.off_topic import classify_input
from rag.services.agent_service.llm import Llm
from rag.services.agent_service.prompts import (
    BLOCKED_MESSAGE,
    OFF_TOPIC_INSTRUCTION,
    PLANNING_INSTRUCTIONS,
    RAG_SYSTEM_PROMPT,
    REVISION_INSTRUCTION,
    TURN_FAILED_MESSAGE,
)
from rag.services.agent_service.streaming import (
    ANSWER_VERIFICATION,
    INPUT_BLOCKED,
    AnswerGate,
    parse_event,
)
from rag.services.agent_service.tools import search_tool
from rag.services.agent_service.turn import is_final_answer, remember

logger = logging.getLogger(__name__)

# Times verify sends an answer back to revise per turn; past it, the last answer ships.
MAX_REVISIONS = 1

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip costs two (model, tools), each checked answer one more (verify).
RECURSION_LIMIT = 75

# Where classify and verify go next. LangGraph's END is typed as a plain str, so the
# routes name it by its value.
_Next = Literal["model", "__end__"]


class ChatState(MessagesState):
    decision: NotRequired[
        InputDecision
    ]  # the off-topic guard's verdict on the turn's question
    todos: NotRequired[list[Todo]]  # the plan, which write_todos replaces whole
    revisions: NotRequired[int]  # answers sent back to revise this turn


class RagAgent:
    """The RAG agent (an AgentPort), grounded in the knowledge base, on this graph:

        START -> classify -> model <-> tools
                    |          |
                   END      verify -> END, or back to model to revise

    `classify` ends a blocked question's turn before the model runs; `verify` checks a
    final answer against the turn's searches, sending it back up to `MAX_REVISIONS`
    times. Every LLM call, the model's and the guards', is tried up to
    `llm.attempts` times; then a model call's error ends the turn (see `AgentTurn`).
    Instructions for one model call (declining an off-topic question, revising an
    answer) are added to that call only, never saved to the thread, so they can't leak
    into later turns. It keeps nothing between turns but the off-topic guard's
    verdicts, in `verdicts`.
    """

    def __init__(
        self,
        llm: Llm,
        search: SearchPort,
        *,
        verdicts: CachePort[InputVerdict],
    ):
        tools = [search_tool(search), write_todos]
        self._on_topic_model = llm.model.bind_tools(tools)
        # Off-topic, the model gets no tools: it is only to decline.
        self._off_topic_model = llm.model
        # For the guards' LLM calls. Untraced of their own, they join the turn's trace;
        # each raises once its retries run out, and each guard fails open.
        self._llm = llm
        self._trace_config = llm.trace_config
        self._verdicts = verdicts  # the off-topic guard's

        graph = StateGraph(ChatState)
        graph.add_node("classify", self._classify)
        # "model" is the node whose output the user sees (see streaming.parse_event).
        graph.add_node(
            "model",
            self._model,
            retry_policy=RetryPolicy(max_attempts=llm.attempts, retry_on=Exception),
        )
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("verify", self._verify)
        graph.add_edge(START, "classify")
        graph.add_conditional_edges("model", _after_model)
        graph.add_edge("tools", "model")
        self.graph = graph.compile()

    def stream(
        self, message: str, history: Sequence[AgentMemory], ctx: RunContext
    ) -> "AgentTurn":
        """Answers `message`, given the agent's memory of each earlier turn."""
        question = HumanMessage(content=message, id=str(uuid.uuid4()))
        # The earlier turns' messages, as the state types them.
        earlier = cast(
            list[AnyMessage], [m for turn in history for m in messages_from_dict(turn)]
        )
        run = self.graph.astream_events(
            ChatState(messages=[*earlier, question]),
            config={
                "recursion_limit": RECURSION_LIMIT,
                **self._trace_config("chat", ctx),
            },
            version="v2",
        )
        return AgentTurn(run, question)

    async def _classify(self, state: ChatState) -> Command[_Next]:
        """A blocked question gets the fixed refusal and is dropped from the thread, so
        no later turn's model call sees it.
        """
        decision = await classify_input(self._llm, state["messages"], self._verdicts)
        if decision != "block":
            return Command(goto="model", update={"decision": decision})

        await adispatch_custom_event(INPUT_BLOCKED, {"message": BLOCKED_MESSAGE})
        question = state["messages"][-1]
        # The thread's reducer gives every message an id.
        assert question.id is not None
        return Command(
            goto="__end__", update={"messages": [RemoveMessage(id=question.id)]}
        )

    async def _model(self, state: ChatState) -> dict[str, Any]:
        off_topic = state.get("decision") == "restrict"
        messages: list[BaseMessage] = [
            SystemMessage(_system_prompt(off_topic=off_topic)),
            *state["messages"],
        ]
        # The model only runs right after a final answer when verify rejected it.
        if is_final_answer(state["messages"][-1]):
            messages.append(HumanMessage(REVISION_INSTRUCTION))

        model = self._off_topic_model if off_topic else self._on_topic_model
        return {"messages": [await model.ainvoke(messages)]}

    async def _verify(self, state: ChatState) -> Command[_Next]:
        """The stream holds a checked answer back until its verdict (`AnswerGate`), so
        a rejected answer never reaches the user.
        """
        revisions = state.get("revisions", 0)
        inputs = verification_inputs(state["messages"])
        if revisions >= MAX_REVISIONS or inputs is None:
            return Command(goto="__end__")

        # The check is a whole LLM call the answer is held back for: the client shows it.
        await adispatch_custom_event(ANSWER_VERIFICATION, {"status": "pending"})
        grounded = await is_grounded(self._llm, *inputs)
        await adispatch_custom_event(
            ANSWER_VERIFICATION, {"status": "done", "grounded": grounded}
        )
        if grounded:
            return Command(goto="__end__")
        return Command(goto="model", update={"revisions": revisions + 1})


def _system_prompt(*, off_topic: bool) -> str:
    """Off-topic, the model is told to decline, and not to plan with a tool it doesn't
    have.
    """
    steps = (
        [OFF_TOPIC_INSTRUCTION]
        if off_topic
        else [WRITE_TODOS_SYSTEM_PROMPT, PLANNING_INSTRUCTIONS]
    )
    return "\n\n".join([RAG_SYSTEM_PROMPT, *steps])


def _after_model(state: ChatState) -> Literal["tools", "verify"]:
    """Tool calls run; an answer is checked."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "verify"


class AgentTurn:
    """One turn: iterate it for its events, as the user is to see them (see
    `AnswerGate`), then what its tools handed the user. Once they end, `memory` holds
    the turn's messages, from the question on; it stays None for a turn to forget: a
    blocked question, a failed tool or model call (whose unanswered tool call the
    model's API would reject in every later turn), or a stream its caller stopped
    reading.
    """

    def __init__(self, run: AsyncIterator[Any], question: HumanMessage):
        self._run = run
        self._question = question
        self._messages: list[BaseMessage] = []  # the run's, once it ends
        self.memory: AgentMemory | None = None

    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        """If a tool or the model fails, the turn ends with `TurnFailed` instead."""
        try:
            async for event in self._gated_events():
                yield event
            self.memory, artifacts = remember(self._messages, self._question)
            if artifacts is not None:
                yield artifacts
        except Exception:
            logger.exception("chat turn failed")
            self.memory = None
            yield TurnFailed(message=TURN_FAILED_MESSAGE)

    async def _gated_events(self) -> AsyncIterator[StreamEvent]:
        gate = AnswerGate()
        async for raw_event in self._run:
            # The run's own end (it has no parent) carries the final state.
            if raw_event["event"] == "on_chain_end" and not raw_event["parent_ids"]:
                self._messages = raw_event["data"]["output"]["messages"]
            for released in [r for e in parse_event(raw_event) for r in gate.feed(e)]:
                yield released
        for released in gate.flush():
            yield released
