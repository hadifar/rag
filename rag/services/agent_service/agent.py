from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict

from langchain.agents.middleware.todo import Todo
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from rag.domain.models import (
    AgentMemory,
    AttachmentFile,
    InputDecision,
    InputVerdict,
    RunContext,
    Skill,
)
from rag.domain.ports import CachePort, SearchPort, SkillsPort
from rag.services.agent_service.attachments import (
    attachments_of,
    question_message,
    with_attachments,
)
from rag.services.agent_service.guards.answer import answer_to_check
from rag.services.agent_service.guards.input import check_input
from rag.services.agent_service.llm import Llm
from rag.services.agent_service.memory import HistoryLimits, recall
from rag.services.agent_service.messages import is_final_answer
from rag.services.agent_service.prompts import (
    BLOCKED_MESSAGE,
    DECLINE_SYSTEM_PROMPT,
    REVISION_INSTRUCTION,
    system_prompt,
)
from rag.services.agent_service.skills import invoked_skill, skill_to_messages
from rag.services.agent_service.streaming import (
    AgentTurn,
    answer_check_started,
    answer_checked,
    input_blocked,
)
from rag.services.agent_service.tools import agent_tools

# Times check_answer sends an answer back to revise per turn; past it, the last answer ships.
MAX_REVISIONS = 1

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip costs two (model, tools), each checked answer one more (check_answer).
RECURSION_LIMIT = 75

# What check_answer does with the turn's answer: ship it, or send it back to the model.
AnswerDecision = Literal["accept", "revise"]


class ChatState(MessagesState):
    input_decision: NotRequired[InputDecision]
    todos: NotRequired[list[Todo]]
    answer_decision: NotRequired[AnswerDecision]
    revisions: NotRequired[int]
    attachments: NotRequired[dict[str, AttachmentFile]]
    skills: NotRequired[list[Skill]]


class ChatUpdate(TypedDict, total=False):
    """What a node returns: the ChatState keys it changes (messages are appended)."""

    messages: list[BaseMessage]
    input_decision: InputDecision
    answer_decision: AnswerDecision
    revisions: int
    skills: list[Skill]


class RagAgent:
    """The RAG agent (an AgentPort):

    START -> check_input -allow-----> load_skills -> model <-> tools
                         -off_topic-> decline -> END     |
                         -block-----> END                check_answer -> END, or model

    """

    def __init__(
        self,
        llm: Llm,
        search: SearchPort,
        skills: SkillsPort,
        *,
        input_verdicts: CachePort[InputVerdict],
        history_limits: HistoryLimits | None = None,
    ):
        tools = agent_tools(search, skills)
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
        self._input_verdicts = input_verdicts
        self._skills = skills
        self._history_limits = history_limits or HistoryLimits()  # see `recall`

        self.graph = self._init_graph(tools)

    def _init_graph(self, tools):
        graph = StateGraph(ChatState, context_schema=RunContext)
        graph.add_node("check_input", self._check_input)
        graph.add_node("load_skills", self._load_skills)
        graph.add_node("decline", self._decline)
        graph.add_node("model", self._model)
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("check_answer", self._check_answer)

        graph.add_edge(START, "check_input")
        graph.add_conditional_edges(
            "check_input",
            _after_input,
            {"allow": "load_skills", "off_topic": "decline", "block": END},
        )
        graph.add_edge("load_skills", "model")
        graph.add_edge("decline", END)
        graph.add_conditional_edges("model", _after_model)
        graph.add_edge("tools", "model")
        graph.add_conditional_edges(
            "check_answer", _after_answer, {"accept": END, "revise": "model"}
        )
        return graph.compile()

    def stream(
        self,
        message: str,
        history: Sequence[AgentMemory],
        ctx: RunContext,
        *,
        attachments: Sequence[AttachmentFile] = (),
        earlier_attachments: Sequence[AttachmentFile] = (),
    ) -> AgentTurn:
        """Answers `message` and its `attachments`"""
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

    async def _check_input(self, state: ChatState) -> ChatUpdate:
        """A blocked question gets the fixed refusal and is dropped from the thread, so
        no later turn's model call sees it.
        """
        question = state["messages"][-1]
        decision = await check_input(
            self._llm,
            state["messages"],
            self._input_verdicts,
            attachments_of(question, state.get("attachments", {})),
        )

        if decision != "block":
            return {"input_decision": decision}

        await input_blocked(BLOCKED_MESSAGE)

        assert question.id is not None
        return {"input_decision": decision, "messages": [RemoveMessage(id=question.id)]}

    async def _load_skills(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> ChatUpdate:
        """The user's skills, for the model's system prompt to list, and, for a question
        that starts with "/<name>" of one of them, that skill loaded at the turn's
        start; a name the user has no skill of loads nothing.
        """
        user = runtime.context.user_id
        update: ChatUpdate = {"skills": await self._skills.list_for_user(user)}
        name = invoked_skill(state["messages"][-1].text)
        if name is None:
            return update
        content = await self._skills.content(user, name)
        if content is not None:
            update["messages"] = skill_to_messages(name, content)
        return update

    async def _model(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> ChatUpdate:
        system = system_prompt(state.get("skills", []))
        messages = _model_messages(system, state)

        # when check_answer rejected previous answer.
        if is_final_answer(state["messages"][-1]):
            messages.append(HumanMessage(REVISION_INSTRUCTION))

        ctx = runtime.context
        model = self._llm.prepare(self._on_topic_models[ctx.model], ctx.effort)
        return {"messages": [await model.ainvoke(messages)]}

    async def _decline(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> ChatUpdate:
        """An off-topic question's reply is fixed, and the turn ends."""

        ctx = runtime.context
        model = self._llm.prepare(self._off_topic_models[ctx.model], ctx.effort)
        messages = _model_messages(DECLINE_SYSTEM_PROMPT, state)
        return {"messages": [await model.ainvoke(messages)]}

    async def _check_answer(self, state: ChatState) -> ChatUpdate:
        """The stream holds a checked answer back until its verdict (`AnswerGate`), so
        a rejected answer never reaches the user.
        """
        check = answer_to_check(state["messages"], state.get("attachments", {}))
        if check is None:
            return {"answer_decision": "accept"}

        # The check is a whole LLM call the answer is held back for: the client shows it.
        await answer_check_started()
        grounded = await check.passes(self._llm)
        await answer_checked(grounded)
        if grounded:
            return {"answer_decision": "accept"}
        return {
            "answer_decision": "revise",
            "revisions": state.get("revisions", 0) + 1,
        }


def _model_messages(system: str, state: ChatState) -> list[BaseMessage]:
    """A model call's messages: `system`, then the thread with its attachments."""
    return [
        SystemMessage(system),
        *with_attachments(state["messages"], state.get("attachments", {})),
    ]


def _after_input(state: ChatState) -> InputDecision:
    """The input guard's decision picks the route (see the path map in `_init_graph`)."""
    decision = state.get("input_decision")
    assert decision is not None  # check_input always sets it
    return decision


def _after_answer(state: ChatState) -> AnswerDecision:
    """The answer guard's decision picks the route (see the path map in `_init_graph`)."""
    decision = state.get("answer_decision")
    assert decision is not None  # check_answer always sets it
    return decision


def _after_model(state: ChatState) -> Literal["tools", "check_answer", "__end__"]:
    """Tool calls run; an answer is checked while the turn may still revise it."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "check_answer" if state.get("revisions", 0) < MAX_REVISIONS else "__end__"
