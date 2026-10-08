from collections.abc import Sequence
from typing import Any, Literal, NotRequired

from langchain.agents.middleware.todo import Todo, write_todos
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
)
from rag.domain.ports import CachePort, SearchPort, SkillsPort
from rag.services.agent_service.attachments import (
    attachments_of,
    question_message,
    with_attachments,
)
from rag.services.agent_service.guards.groundedness import answer_to_check
from rag.services.agent_service.guards.off_topic import classify_input
from rag.services.agent_service.llm import Llm
from rag.services.agent_service.memory import HistoryLimits, recall
from rag.services.agent_service.messages import is_final_answer
from rag.services.agent_service.prompts import (
    BLOCKED_MESSAGE,
    REVISION_INSTRUCTION,
    system_prompt,
)
from rag.services.agent_service.skills import (
    invoked_skill,
    loaded_skill,
    skill_file_tool,
    skill_loaded,
    skill_tool,
)
from rag.services.agent_service.streaming import (
    ANSWER_VERIFICATION,
    INPUT_BLOCKED,
    AgentTurn,
)
from rag.services.agent_service.tools import search_tool

# Times verify sends an answer back to revise per turn; past it, the last answer ships.
MAX_REVISIONS = 1

# Graph steps a turn may take before LangGraph stops it (its default is 25). Each tool
# round trip costs two (model, tools), each checked answer one more (verify).
RECURSION_LIMIT = 75

# Where classify and verify go next. LangGraph's END is typed as a plain str, so the
# routes name it by its value.
_Next = Literal["model", "__end__"]
_Classified = Literal["invoke_skill", "model", "__end__"]


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
                  |    |                      ^  |
                  |    +---- off-topic -------+  |
                 END                          verify -> END, or back to model to revise

    `classify` ends a blocked question's turn before the model runs, and sends an
    off-topic one straight to the model, which is only to decline; `invoke_skill`
    loads the skill a question invokes ("/<name> ..."); `verify` checks a
    final answer against the turn's searches, sending it back up to `MAX_REVISIONS`
    times, after which the model's answer ends the turn unchecked. Every LLM call, the
    model's and the guards', is tried up to `llm.attempts` times; then a model call's
    error ends the turn (see `AgentTurn`).
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

        self.graph = self._init_graph(tools)

    def _init_graph(self, tools):
        graph = StateGraph(ChatState, context_schema=RunContext)
        graph.add_node("classify", self._classify)
        graph.add_node("invoke_skill", self._invoke_skill)
        graph.add_node(
            "model",
            self._model,
            retry_policy=RetryPolicy(
                max_attempts=self._llm.attempts, retry_on=Exception
            ),
        )
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("verify", self._verify)

        graph.add_edge(START, "classify")
        graph.add_edge("invoke_skill", "model")
        graph.add_conditional_edges("model", _after_model)
        graph.add_edge("tools", "model")
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

        if decision == "restrict":
            return Command(goto="model", update={"decision": decision})

        if decision == "allow":
            return Command(goto="invoke_skill", update={"decision": decision})

        await adispatch_custom_event(INPUT_BLOCKED, {"message": BLOCKED_MESSAGE})

        assert question.id is not None
        return Command(
            goto="__end__", update={"messages": [RemoveMessage(id=question.id)]}
        )

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
        return {"messages": skill_loaded(name, loaded_skill(content))}

    async def _model(
        self, state: ChatState, runtime: Runtime[RunContext]
    ) -> dict[str, Any]:
        off_topic = state.get("decision") == "restrict"
        skills = state.get("skills")
        if skills is None:
            skills = await self._skills.list_for_user(runtime.context.user_id)
        messages: list[BaseMessage] = [
            SystemMessage(system_prompt(off_topic=off_topic, skills=skills)),
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
        check = answer_to_check(state["messages"], state.get("attachments", {}))
        if check is None:
            return Command(goto="__end__")

        # The check is a whole LLM call the answer is held back for: the client shows it.
        await adispatch_custom_event(ANSWER_VERIFICATION, {"status": "pending"})
        grounded = await check.passes(self._llm)
        await adispatch_custom_event(
            ANSWER_VERIFICATION, {"status": "done", "grounded": grounded}
        )
        if grounded:
            return Command(goto="__end__")
        return Command(
            goto="model", update={"revisions": state.get("revisions", 0) + 1}
        )


def _after_model(state: ChatState) -> Literal["tools", "verify", "__end__"]:
    """Tool calls run; an answer is checked while the turn may still revise it."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "verify" if state.get("revisions", 0) < MAX_REVISIONS else "__end__"
