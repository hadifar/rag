from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict

from langchain.agents.middleware.todo import Todo
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
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
from rag.services.agent_service.guards.input import check_input
from rag.services.agent_service.llm import Llm
from rag.services.agent_service.memory import HistoryLimits, recall
from rag.services.agent_service.prompts import (
    ANSWER_SYSTEM_PROMPT,
    BLOCKED_MESSAGE,
    DECLINE_SYSTEM_PROMPT,
    research_prompt,
)
from rag.services.agent_service.skills import invoked_skill, skill_to_messages
from rag.services.agent_service.streaming import AgentTurn, input_blocked
from rag.services.agent_service.tools import agent_tools

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip costs two (research, tools).
RECURSION_LIMIT = 75


class ChatState(MessagesState):
    input_decision: NotRequired[InputDecision]
    todos: NotRequired[list[Todo]]
    attachments: NotRequired[dict[str, AttachmentFile]]
    skills: NotRequired[list[Skill]]


class ChatUpdate(TypedDict, total=False):
    """What a node returns: the ChatState keys it changes (messages are appended)."""

    messages: list[BaseMessage]
    input_decision: InputDecision
    skills: list[Skill]


class RagAgent:
    """The RAG agent (an AgentPort):

    START -> check_input -allow-----> load_skills -> research <-> tools
                         -off_topic-> decline -> END     |
                         -block-----> END                answer -> END

    research gathers the evidence and never speaks to the user; answer writes the
    answer from it.
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
        self._research_models = {
            name: model.bind_tools(tools) for name, model in llm.models.items()
        }
        # The tools stay bound, unusable, so the API accepts research's tool calls in
        # the thread; the answer is written from what they returned.
        self._answer_models = {
            name: model.bind_tools(tools, tool_choice="none")
            for name, model in llm.models.items()
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
        graph.add_node("research", self._research)
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("answer", self._answer)

        graph.add_edge(START, "check_input")
        graph.add_conditional_edges(
            "check_input",
            _after_input,
            {"allow": "load_skills", "off_topic": "decline", "block": END},
        )
        graph.add_edge("load_skills", "research")
        graph.add_edge("decline", END)
        graph.add_conditional_edges("research", _after_research)
        graph.add_edge("tools", "research")
        graph.add_edge("answer", END)
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

    async def _research(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> ChatUpdate:
        """Plans and searches. Its reply without tool calls only says it's done: it's
        left out of the thread, so the turn's only answer is the answer node's.
        """
        system = research_prompt(state.get("skills", []))
        ctx = runtime.context
        model = self._llm.prepare(self._research_models[ctx.model], ctx.effort)
        reply = await model.ainvoke(_model_messages(system, state))
        if not reply.tool_calls:
            return {}
        return {"messages": [reply]}

    async def _answer(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> ChatUpdate:
        """The answer, from what research found."""
        ctx = runtime.context
        model = self._llm.prepare(self._answer_models[ctx.model], ctx.effort)
        messages = _model_messages(ANSWER_SYSTEM_PROMPT, state)
        return {"messages": [await model.ainvoke(messages)]}

    async def _decline(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> ChatUpdate:
        """An off-topic question's reply is fixed, and the turn ends."""

        ctx = runtime.context
        model = self._llm.prepare(self._off_topic_models[ctx.model], ctx.effort)
        messages = _model_messages(DECLINE_SYSTEM_PROMPT, state)
        return {"messages": [await model.ainvoke(messages)]}


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


def _after_research(state: ChatState) -> Literal["tools", "answer"]:
    """Tool calls run; once research stops calling them, the answer is written."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "answer"
