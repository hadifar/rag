from collections.abc import Sequence
from typing import Any, Literal, NotRequired

from langchain.agents.middleware.todo import Todo
from langchain_core.callbacks import adispatch_custom_event
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
    REVISION_INSTRUCTION,
    system_prompt,
)
from rag.services.agent_service.skills import invoked_skill, skill_to_messages
from rag.services.agent_service.streaming import (
    ANSWER_CHECK,
    INPUT_BLOCKED,
    AgentTurn,
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
    input_decision: NotRequired[InputDecision]  # the input guard's, on the question
    todos: NotRequired[list[Todo]]  # the plan, which write_todos replaces whole
    answer_decision: NotRequired[
        AnswerDecision
    ]  # the answer guard's, on the last answer
    revisions: NotRequired[int]  # answers sent back to revise this turn
    # The thread's attachments by id: its messages list ids, each model call reads these.
    attachments: NotRequired[dict[str, AttachmentFile]]
    # The user's skills, loaded on the turn's first model call.
    skills: NotRequired[list[Skill]]


class RagAgent:
    """The RAG agent (an AgentPort):

    START -> check_input -> invoke_skill -> model <-> tools
               |    |                        ^  |
               |    +----- off_topic --------+  |
              END                         check_answer -> END, or  model

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
        graph.add_node("invoke_skill", self._invoke_skill)
        graph.add_node("model", self._model)
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("check_answer", self._check_answer)

        graph.add_edge(START, "check_input")
        graph.add_conditional_edges(
            "check_input",
            _after_input,
            {"allow": "invoke_skill", "off_topic": "model", "block": END},
        )
        graph.add_edge("invoke_skill", "model")
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

    async def _check_input(self, state: ChatState) -> dict[str, Any]:
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

        await adispatch_custom_event(INPUT_BLOCKED, {"message": BLOCKED_MESSAGE})

        assert question.id is not None
        return {"input_decision": decision, "messages": [RemoveMessage(id=question.id)]}

    async def _invoke_skill(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> dict[str, Any]:
        """Only trigger when a question that starts with "/<name>" of one of the user's skills starts its
        turn with that skill loaded; a name the user has no skill of loads nothing.
        """
        name = invoked_skill(state["messages"][-1].text)
        if name is None:
            return {}
        content = await self._skills.content(runtime.context.user_id, name)
        if content is None:
            return {}
        return {"messages": skill_to_messages(name, content)}

    async def _model(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> dict[str, Any]:

        off_topic = state.get("input_decision") == "off_topic"

        skills = state.get("skills")

        if skills is None:
            skills = await self._skills.list_for_user(runtime.context.user_id)

        messages: list[BaseMessage] = [
            SystemMessage(system_prompt(off_topic=off_topic, skills=skills)),
            *with_attachments(state["messages"], state.get("attachments", {})),
        ]

        # The model only runs right after a final answer when check_answer rejected it.
        if is_final_answer(state["messages"][-1]):
            messages.append(HumanMessage(REVISION_INSTRUCTION))

        ctx = runtime.context
        models = self._off_topic_models if off_topic else self._on_topic_models
        model = self._llm.prepare(models[ctx.model], ctx.effort)
        return {"messages": [await model.ainvoke(messages)], "skills": skills}

    async def _check_answer(self, state: ChatState) -> dict[str, Any]:
        """The stream holds a checked answer back until its verdict (`AnswerGate`), so
        a rejected answer never reaches the user.
        """
        check = answer_to_check(state["messages"], state.get("attachments", {}))
        if check is None:
            return {"answer_decision": "accept"}

        # The check is a whole LLM call the answer is held back for: the client shows it.
        await adispatch_custom_event(ANSWER_CHECK, {"status": "pending"})
        grounded = await check.passes(self._llm)
        await adispatch_custom_event(
            ANSWER_CHECK, {"status": "done", "grounded": grounded}
        )
        if grounded:
            return {"answer_decision": "accept"}
        return {
            "answer_decision": "revise",
            "revisions": state.get("revisions", 0) + 1,
        }


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
