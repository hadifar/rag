import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal, NotRequired

from langchain.agents.middleware.todo import (
    WRITE_TODOS_SYSTEM_PROMPT,
    Todo,
    write_todos,
)
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command, RetryPolicy

from rag.domain.models import (
    AgentMemory,
    AttachmentFile,
    InputDecision,
    InputVerdict,
    RunContext,
    Skill,
    StreamEvent,
    TurnFailed,
)
from rag.domain.ports import CachePort, SearchPort, SkillsPort
from rag.services.agent_service.attachments import (
    attachments_of,
    question_message,
    text_of,
    with_attachments,
)
from rag.services.agent_service.guards.groundedness import (
    is_grounded,
    verification_inputs,
)
from rag.services.agent_service.guards.off_topic import classify_input
from rag.services.agent_service.history import HistoryLimits, recall
from rag.services.agent_service.llm import Llm
from rag.services.agent_service.prompts import (
    ATTACHMENTS_INSTRUCTION,
    BLOCKED_MESSAGE,
    OFF_TOPIC_INSTRUCTION,
    PLANNING_INSTRUCTIONS,
    RAG_SYSTEM_PROMPT,
    REVISION_INSTRUCTION,
    SKILLS_INSTRUCTION,
    TURN_FAILED_MESSAGE,
)
from rag.services.agent_service.streaming import (
    ANSWER_VERIFICATION,
    INPUT_BLOCKED,
    AnswerGate,
    parse_event,
)
from rag.services.agent_service.skills import invoked_skill, skill_loaded
from rag.services.agent_service.tools import (
    loaded_skill,
    search_tool,
    skill_file_tool,
    skill_tool,
)
from rag.services.agent_service.turn import current_turn, is_final_answer, remember

logger = logging.getLogger(__name__)

# Times verify sends an answer back to revise per turn; past it, the last answer ships.
MAX_REVISIONS = 1

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip costs two (model, tools), each checked answer one more (verify).
RECURSION_LIMIT = 75

# Where classify and verify go next. LangGraph's END is typed as a plain str, so the
# routes name it by its value.
_Next = Literal["model", "__end__"]
_Classified = Literal["invoke_skill", "__end__"]


class ChatState(MessagesState):
    decision: NotRequired[
        InputDecision
    ]  # the off-topic guard's verdict on the turn's question
    todos: NotRequired[list[Todo]]  # the plan, which write_todos replaces whole
    revisions: NotRequired[int]  # answers sent back to revise this turn
    # The thread's attachments by id: its messages list ids, each model call reads these.
    attachments: NotRequired[dict[str, AttachmentFile]]
    # The user's skills, loaded on the turn's first model call.
    skills: NotRequired[list[Skill]]


class RagAgent:
    """The RAG agent (an AgentPort), grounded in the knowledge base, on this graph:

        START -> classify -> invoke_skill -> model <-> tools
                    |                          |
                   END                      verify -> END, or back to model to revise

    `classify` ends a blocked question's turn before the model runs; `invoke_skill`
    loads the skill a question invokes ("/<name> ..."); `verify` checks a
    final answer against the turn's searches, sending it back up to `MAX_REVISIONS`
    times. Every LLM call, the model's and the guards', is tried up to
    `llm.attempts` times; then a model call's error ends the turn (see `AgentTurn`).
    The model sees the name and description of each of the user's `skills`, and loads
    one's instructions with a tool when a question fits it.
    Instructions for one model call (declining an off-topic question, revising an
    answer) are added to that call only, never saved to the thread, so they can't leak
    into later turns. It keeps nothing between turns but the off-topic guard's
    verdicts, in `verdicts`.
    """

    def __init__(
        self,
        llm: Llm,
        search: SearchPort,
        skills: SkillsPort,
        *,
        verdicts: CachePort[InputVerdict],
        history_limits: HistoryLimits | None = None,
    ):
        tools = [
            search_tool(search),
            skill_tool(skills),
            skill_file_tool(skills),
            write_todos,
        ]
        # One of each per model a conversation can be set to.
        self._on_topic_models = {
            name: model.bind_tools(tools) for name, model in llm.models.items()
        }
        # Off-topic, the model gets no tools: it is only to decline.
        self._off_topic_models = llm.models
        # For the guards' LLM calls. Untraced of their own, they join the turn's trace;
        # each raises once its retries run out, and each guard fails open.
        self._llm = llm
        self._trace_config = llm.trace_config
        self._verdicts = verdicts  # the off-topic guard's
        self._skills = skills
        self._history_limits = history_limits or HistoryLimits()  # see `recall`

        # The turn's RunContext: whose skills the model sees and load_skill reads.
        graph = StateGraph(ChatState, context_schema=RunContext)
        graph.add_node("classify", self._classify)
        graph.add_node("invoke_skill", self._invoke_skill)
        # "model" is the node whose output the user sees (see streaming.parse_event).
        graph.add_node(
            "model",
            self._model,
            retry_policy=RetryPolicy(max_attempts=llm.attempts, retry_on=Exception),
        )
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("verify", self._verify)
        graph.add_edge(START, "classify")
        graph.add_edge("invoke_skill", "model")
        graph.add_conditional_edges("model", _after_model)
        graph.add_edge("tools", "model")
        self.graph = graph.compile()

    def stream(
        self,
        message: str,
        history: Sequence[AgentMemory],
        ctx: RunContext,
        *,
        attachments: Sequence[AttachmentFile] = (),
        earlier_attachments: Sequence[AttachmentFile] = (),
    ) -> "AgentTurn":
        """Answers `message` and its `attachments`, given the agent's memory of each
        earlier turn (compacted and cut to fit, see `recall`) and the attachments those
        were sent with.
        """
        question = question_message(message, attachments)
        earlier = recall(history, self._history_limits)
        files = {str(f.attachment.id): f for f in [*earlier_attachments, *attachments]}
        run = self.graph.astream_events(
            ChatState(messages=[*earlier, question], attachments=files),
            config={
                "recursion_limit": RECURSION_LIMIT,
                **self._trace_config("chat", ctx),
            },
            context=ctx,
            version="v2",
        )
        return AgentTurn(run, question)

    async def _classify(self, state: ChatState) -> Command[_Classified]:
        """A blocked question gets the fixed refusal and is dropped from the thread, so
        no later turn's model call sees it.
        """
        question = state["messages"][-1]
        decision = await classify_input(
            self._llm,
            state["messages"],
            self._verdicts,
            attachments_of(question, state.get("attachments", {})),
        )
        if decision != "block":
            return Command(goto="invoke_skill", update={"decision": decision})

        await adispatch_custom_event(INPUT_BLOCKED, {"message": BLOCKED_MESSAGE})
        # The thread's reducer gives every message an id.
        assert question.id is not None
        return Command(
            goto="__end__", update={"messages": [RemoveMessage(id=question.id)]}
        )

    async def _invoke_skill(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> dict[str, Any]:
        """A question that starts with "/<name>" of one of the user's skills starts its
        turn with that skill loaded. Off-topic, the model is only to decline, so it
        loads nothing; nor for a name the user has no skill of.
        """
        name = invoked_skill(state["messages"][-1].text)
        if name is None or state.get("decision") == "restrict":
            return {}
        content = await self._skills.content(runtime.context.user_id, name)
        if content is None:
            return {}
        return {"messages": skill_loaded(name, loaded_skill(content))}

    async def _model(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> dict[str, Any]:
        off_topic = state.get("decision") == "restrict"
        skills = state.get("skills")
        if skills is None:
            skills = await self._skills.list_for_user(runtime.context.user_id)
        messages: list[BaseMessage] = [
            SystemMessage(_system_prompt(off_topic=off_topic, skills=skills)),
            *with_attachments(state["messages"], state.get("attachments", {})),
        ]
        # The model only runs right after a final answer when verify rejected it.
        if is_final_answer(state["messages"][-1]):
            messages.append(HumanMessage(REVISION_INSTRUCTION))

        ctx = runtime.context
        models = self._off_topic_models if off_topic else self._on_topic_models
        model = self._llm.with_effort(models[ctx.model], ctx.effort)
        return {"messages": [await model.ainvoke(messages)], "skills": skills}

    async def _verify(self, state: ChatState) -> Command[_Next]:
        """The stream holds a checked answer back until its verdict (`AnswerGate`), so
        a rejected answer never reaches the user.
        """
        revisions = state.get("revisions", 0)
        question = current_turn(state["messages"])[0]
        attached = text_of(attachments_of(question, state.get("attachments", {})))
        inputs = verification_inputs(state["messages"], attached)
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


def _system_prompt(*, off_topic: bool, skills: Sequence[Skill] = ()) -> str:
    """Off-topic, the model is told to decline, and not to plan or load skills with
    tools it doesn't have.
    """
    if off_topic:
        steps = [OFF_TOPIC_INSTRUCTION]
    else:
        steps = [WRITE_TODOS_SYSTEM_PROMPT, PLANNING_INSTRUCTIONS]
        if skills:
            listed = "\n".join(f"- {s.name}: {s.description}" for s in skills)
            steps.append(SKILLS_INSTRUCTION.format(skills=listed))
    return "\n\n".join([RAG_SYSTEM_PROMPT, ATTACHMENTS_INSTRUCTION, *steps])


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
