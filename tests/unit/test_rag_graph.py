"""Multi-turn tests for the agent graph: per-turn state must not leak into later turns."""

import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import Field

from rag.domain.models import (
    AnswerRetracted,
    AnswerVerified,
    Chunk,
    OffTopicMiddleware,
    ReferencesReady,
    RunContext,
    StreamEvent,
    TextDelta,
    Tool,
    ToolAgentSpec,
    ToolCall,
    ToolResult,
)
from rag.services.agent_service.middleware.groundness import REVISION_INSTRUCTION
from rag.services.agent_service.middleware.topical import OFF_TOPIC_INSTRUCTION
from rag.services.agent_service.service import Agent, AgentService
from rag.services.preference_service.service import PreferenceService
from rag.services.rag_service.prompts import PLANNING_INSTRUCTIONS
from rag.services.rag_service.service import RagService
from rag.services.rag_service.tools import search_tool
from tests.unit.fakes import FakePreferenceRepository


class _ScriptedChatModel(BaseChatModel):
    """Answers the guards' classifier prompts from the verdict lists, and every other
    call (the agent's) from `answers`, in order. Records what each agent call saw.
    """

    answers: list[AIMessage]
    off_topic_messages: set[str] = Field(default_factory=set)
    groundedness_verdicts: list[str] = Field(default_factory=list)
    agent_calls: list[dict[str, Any]] = Field(default_factory=list)
    verifier_calls: list[str] = Field(default_factory=list)
    bound_tools: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self.model_copy(update={"bound_tools": [tool.name for tool in tools]})

    def _reply(self, messages: list[BaseMessage]) -> AIMessage:
        prompt = str(messages[-1].content)
        if prompt.startswith("You are a scope classifier"):
            message = prompt.rsplit("MESSAGE:\n", 1)[1]
            return AIMessage(
                content="IRRELEVANT"
                if message in self.off_topic_messages
                else "RELEVANT"
            )
        if prompt.startswith("You are a strict fact-checker"):
            self.verifier_calls.append(prompt)
            verdict = (
                self.groundedness_verdicts.pop(0)
                if self.groundedness_verdicts
                else "GROUNDED"
            )
            return AIMessage(content=verdict)

        self.agent_calls.append({"messages": messages, "tools": self.bound_tools})
        return self.answers.pop(0)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        reply = self._reply(messages)
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content=reply.content,
                tool_call_chunks=[
                    {
                        "name": call["name"],
                        "args": json.dumps(call["args"]),
                        "id": call["id"],
                        "index": index,
                    }
                    for index, call in enumerate(reply.tool_calls)
                ],
            )
        )


_NO_RESULTS_QUERY = "nothing"


class _StubRetrievalService:
    """Returns one document whose source_id is the query itself, or none for
    _NO_RESULTS_QUERY.
    """

    async def search(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        if query == _NO_RESULTS_QUERY:
            return []
        return [
            (
                Chunk(text=f"facts about {query}", metadata={"source_id": query}),
                1.0,
            )
        ]


def _search(query: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "search_kb", "args": {"query": query}, "id": str(uuid.uuid4())}
        ],
    )


def _answer(text: str) -> AIMessage:
    return AIMessage(content=text)


def _no_tracing(name: str | None) -> RunnableConfig:
    return {}


_USER = uuid.uuid4()
_CONVERSATION = uuid.uuid4()
_PREFERENCE_TOOLS = ["forget_user_preference", "save_user_preference"]


class _Chat:
    def __init__(self, model: _ScriptedChatModel):
        self.preferences = PreferenceService(FakePreferenceRepository())
        agents = AgentService(model, InMemorySaver(), _no_tracing, retry_attempts=3)
        self.rag = RagService(
            _StubRetrievalService(),
            agents,
            max_revisions=1,
            capabilities=[self.preferences.capability()],
        )
        agent = self.rag._agent
        assert isinstance(agent, Agent)
        self.graph: CompiledStateGraph = agent._graph
        self.config: RunnableConfig = {
            "configurable": {"thread_id": str(_CONVERSATION)}
        }

    async def send(self, text: str) -> list[StreamEvent]:
        ctx = RunContext(user_id=_USER, conversation_id=_CONVERSATION)
        return [event async for event in self.rag.stream(text, ctx)]

    async def saved_messages(self) -> list[BaseMessage]:
        return (await self.graph.aget_state(self.config)).values["messages"]


def _references(events: list[StreamEvent]) -> list[str]:
    return [
        ref for e in events if isinstance(e, ReferencesReady) for ref in e.references
    ]


def _text(events: list[StreamEvent]) -> str:
    return "".join(e.text for e in events if isinstance(e, TextDelta))


def _is_revision_call(call: dict[str, Any]) -> bool:
    return call["messages"][-1].content == REVISION_INSTRUCTION


async def test_streams_only_the_agents_answer_not_the_guards_verdicts() -> None:
    model = _ScriptedChatModel(answers=[_search("pricing"), _answer("It costs 10.")])

    events = await _Chat(model).send("How much?")

    assert _text(events) == "It costs 10."


async def test_references_cover_only_the_current_turn() -> None:
    model = _ScriptedChatModel(
        answers=[_search("pricing"), _answer("A"), _search("security"), _answer("B")]
    )
    chat = _Chat(model)

    assert _references(await chat.send("first")) == ["pricing"]
    assert _references(await chat.send("second")) == ["security"]


async def test_a_search_that_finds_nothing_sends_empty_references() -> None:
    model = _ScriptedChatModel(
        answers=[_search(_NO_RESULTS_QUERY), _answer("I don't know.")]
    )

    events = await _Chat(model).send("first")

    assert [e for e in events if isinstance(e, ReferencesReady)] == [
        ReferencesReady(references=[])
    ]


async def test_a_turn_without_a_search_sends_no_references() -> None:
    model = _ScriptedChatModel(answers=[_answer("hi!")])

    events = await _Chat(model).send("hello")

    assert not any(isinstance(e, ReferencesReady) for e in events)


async def test_ungrounded_answer_is_revised_again_in_a_later_turn() -> None:
    """The revision counter resets each turn; it used to stay at the cap forever,
    which silently switched the groundedness check off after the first revision.
    """
    model = _ScriptedChatModel(
        answers=[
            _search("pricing"),
            _answer("wrong"),
            _answer("revised"),
            _search("security"),
            _answer("wrong again"),
            _answer("revised again"),
        ],
        groundedness_verdicts=["UNGROUNDED", "UNGROUNDED"],
    )
    chat = _Chat(model)

    await chat.send("first")
    await chat.send("second")

    assert sum(_is_revision_call(call) for call in model.agent_calls) == 2


async def test_revisions_stop_at_the_cap_and_the_last_answer_is_kept() -> None:
    model = _ScriptedChatModel(
        answers=[_search("pricing"), _answer("wrong"), _answer("still wrong")],
        groundedness_verdicts=["UNGROUNDED", "UNGROUNDED"],
    )

    events = await _Chat(model).send("first")

    # max_revisions is 1: one revision, and the revised answer isn't re-verified.
    assert sum(_is_revision_call(call) for call in model.agent_calls) == 1
    assert len(model.verifier_calls) == 1
    assert _text(events).endswith("still wrong")


async def test_a_rejected_answer_is_retracted_before_its_revision_streams() -> None:
    model = _ScriptedChatModel(
        answers=[_search("pricing"), _answer("wrong"), _answer("revised")],
        groundedness_verdicts=["UNGROUNDED"],
    )

    events = await _Chat(model).send("first")

    texts = [e for e in events if isinstance(e, TextDelta | AnswerRetracted)]
    assert texts == [TextDelta("wrong"), AnswerRetracted(), TextDelta("revised")]


async def test_the_answers_check_is_streamed_between_the_answer_and_its_retraction() -> (
    None
):
    model = _ScriptedChatModel(
        answers=[_search("pricing"), _answer("wrong"), _answer("revised")],
        groundedness_verdicts=["UNGROUNDED"],
    )

    events = await _Chat(model).send("first")

    # max_revisions is 1: the revision isn't checked again.
    answer = [
        e for e in events if isinstance(e, TextDelta | AnswerVerified | AnswerRetracted)
    ]
    assert answer == [
        TextDelta("wrong"),
        AnswerVerified(status="pending"),
        AnswerVerified(status="done", grounded=False),
        AnswerRetracted(),
        TextDelta("revised"),
    ]


async def test_an_answer_with_nothing_searched_is_not_checked() -> None:
    model = _ScriptedChatModel(answers=[_answer("hi!")])

    events = await _Chat(model).send("hello")

    assert not any(isinstance(e, AnswerVerified) for e in events)


async def test_a_grounded_answer_is_never_retracted() -> None:
    model = _ScriptedChatModel(answers=[_search("pricing"), _answer("right")])

    events = await _Chat(model).send("first")

    assert not any(isinstance(e, AnswerRetracted) for e in events)


async def test_revision_instruction_is_not_saved_to_the_thread() -> None:
    model = _ScriptedChatModel(
        answers=[_search("pricing"), _answer("wrong"), _answer("revised")],
        groundedness_verdicts=["UNGROUNDED"],
    )
    chat = _Chat(model)

    await chat.send("first")

    saved = [m.content for m in await chat.saved_messages()]
    assert REVISION_INSTRUCTION not in saved
    assert [
        m.content for m in await chat.saved_messages() if isinstance(m, HumanMessage)
    ] == ["first"]


async def test_off_topic_instruction_applies_to_that_turn_only() -> None:
    model = _ScriptedChatModel(
        answers=[
            _answer("I only help with AtlasFlow."),
            _search("pricing"),
            _answer("A"),
        ],
        off_topic_messages={"weather?"},
    )
    chat = _Chat(model)

    await chat.send("weather?")
    await chat.send("pricing?")

    off_topic_call, on_topic_call = model.agent_calls[0], model.agent_calls[1]
    assert OFF_TOPIC_INSTRUCTION in off_topic_call["messages"][0].text
    # Off-topic, the model keeps only the tools about the user, not the product.
    assert sorted(off_topic_call["tools"]) == _PREFERENCE_TOOLS
    assert OFF_TOPIC_INSTRUCTION not in on_topic_call["messages"][0].text
    assert sorted(on_topic_call["tools"]) == sorted(
        ["search_kb", "write_todos", *_PREFERENCE_TOOLS]
    )
    assert PLANNING_INSTRUCTIONS in on_topic_call["messages"][0].text
    assert not any(isinstance(m, SystemMessage) for m in await chat.saved_messages())


@pytest.mark.parametrize("second_turn_searches", [False, True])
async def test_verifier_only_sees_the_current_turns_context(
    second_turn_searches: bool,
) -> None:
    second_turn = (
        [_search("security"), _answer("B")]
        if second_turn_searches
        else [_answer("hi!")]
    )
    model = _ScriptedChatModel(answers=[_search("pricing"), _answer("A"), *second_turn])
    chat = _Chat(model)

    await chat.send("first")
    await chat.send("second")

    # Turn 1 is verified. Turn 2 is verified only if it searched, and then only
    # against its own results, not turn 1's.
    assert len(model.verifier_calls) == (2 if second_turn_searches else 1)
    if second_turn_searches:
        assert "facts about security" in model.verifier_calls[1]
        assert "facts about pricing" not in model.verifier_calls[1]


def test_tools_with_the_same_name_are_rejected_up_front() -> None:
    agents = AgentService(
        _ScriptedChatModel(answers=[]),
        InMemorySaver(),
        _no_tracing,
        retry_attempts=3,
    )
    docs = search_tool(_StubRetrievalService())

    with pytest.raises(ValueError, match="search_kb"):
        agents.create_agent(ToolAgentSpec(system_prompt="", tools=[docs, docs]))


def _call(name: str, **args: str) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": str(uuid.uuid4())}]
    )


async def test_saved_preferences_are_in_every_model_calls_prompt_not_the_thread() -> (
    None
):
    model = _ScriptedChatModel(answers=[_search("pricing"), _answer("Het kost 10.")])
    chat = _Chat(model)
    await chat.preferences.add(_USER, "Answer in Dutch")

    await chat.send("How much?")

    assert all("Answer in Dutch" in c["messages"][0].text for c in model.agent_calls)
    assert not any(isinstance(m, SystemMessage) for m in await chat.saved_messages())


async def test_a_preference_saved_in_one_turn_applies_from_the_next_call_on() -> None:
    model = _ScriptedChatModel(
        answers=[
            _call("save_user_preference", text="Keep answers short"),
            _answer("Noted."),
            _search("pricing"),
            _answer("10."),
        ]
    )
    chat = _Chat(model)

    events = await chat.send("Please always keep answers short")
    await chat.send("How much?")

    assert [p.text for p in await chat.preferences.list_for_user(_USER)] == [
        "Keep answers short"
    ]
    assert "Keep answers short" not in model.agent_calls[0]["messages"][0].text
    assert "Keep answers short" in model.agent_calls[1]["messages"][0].text
    # Saving a preference is no search: the turn cites nothing and isn't verified.
    assert not any(isinstance(e, ReferencesReady) for e in events)
    assert len(model.verifier_calls) == 1  # only the pricing answer


async def test_preferences_are_saved_even_on_an_off_topic_turn() -> None:
    model = _ScriptedChatModel(
        answers=[
            _call("save_user_preference", text="Answer in Dutch"),
            _answer("Opgeslagen."),
        ],
        off_topic_messages={"Always answer in Dutch"},
    )
    chat = _Chat(model)

    await chat.send("Always answer in Dutch")

    assert [p.text for p in await chat.preferences.list_for_user(_USER)] == [
        "Answer in Dutch"
    ]


async def test_forgetting_a_preference_only_reaches_the_users_own() -> None:
    model = _ScriptedChatModel(answers=[])
    chat = _Chat(model)
    mine = await chat.preferences.add(_USER, "Answer in Dutch")
    theirs = await chat.preferences.add(uuid.uuid4(), "Answer in French")
    model.answers.extend(
        [
            _call("forget_user_preference", preference_id=theirs.id),
            _call("forget_user_preference", preference_id=mine.id),
            _answer("Done."),
        ]
    )

    events = await chat.send("Forget my preferences")

    outputs = [e.output for e in events if isinstance(e, ToolCall) and e.output]
    assert outputs == [
        f"No saved preference has the id {theirs.id}.",
        f"Forgot preference {mine.id}.",
    ]
    assert await chat.preferences.list_for_user(_USER) == []


def test_a_tool_cant_take_a_preference_tools_name() -> None:
    agents = AgentService(
        _ScriptedChatModel(answers=[]),
        InMemorySaver(),
        _no_tracing,
        retry_attempts=3,
    )
    clash = Tool(
        name="save_user_preference",
        description="",
        run=search_tool(_StubRetrievalService()).run,
    )
    preferences = PreferenceService(FakePreferenceRepository()).capability()

    with pytest.raises(ValueError, match="save_user_preference"):
        agents.create_agent(
            ToolAgentSpec(system_prompt="", tools=[clash], capabilities=[preferences])
        )


async def test_a_user_tool_gets_the_turns_context_and_is_kept_off_topic() -> None:
    model = _ScriptedChatModel(
        answers=[_call("whoami", query="me"), _answer("You're you.")],
        off_topic_messages={"who am I?"},
    )
    agents = AgentService(model, InMemorySaver(), _no_tracing, retry_attempts=3)
    seen: list[RunContext] = []

    async def whoami(query: str, ctx: RunContext) -> ToolResult:
        seen.append(ctx)
        return ToolResult(str(ctx.user_id))

    agent = agents.create_agent(
        ToolAgentSpec(
            system_prompt="",
            tools=[
                search_tool(_StubRetrievalService()),
                Tool("whoami", "Who the user is.", whoami, kind="user"),
            ],
            middleware=[OffTopicMiddleware()],
        )
    )
    ctx = RunContext(user_id=_USER, conversation_id=_CONVERSATION)

    _ = [event async for event in agent.stream("who am I?", ctx)]

    assert seen == [ctx]
    # Off-topic, the product's search is withheld but the user tool stays.
    assert model.agent_calls[0]["tools"] == ["whoami"]
