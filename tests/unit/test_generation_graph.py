"""Multi-turn tests for the agent graph: per-turn state must not leak into later turns."""

import json
import uuid
from collections.abc import Iterator
from typing import Any, cast

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.documents import Document
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

from rag.domain.events import SourcesReady, StreamEvent, TextDelta
from rag.services.generation_service.graph import build_graph
from rag.services.generation_service.guards.groundness import REVISION_INSTRUCTION
from rag.services.generation_service.guards.topical import OFF_TOPIC_INSTRUCTION
from rag.services.generation_service.streaming import stream_events
from rag.services.generation_service.tools import build_search_tool
from rag.services.generation_service.turn import to_history
from rag.services.retrieval_service.service import RetrievalService


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

    async def search(self, query: str, top_k: int = 3) -> list[tuple[Document, float]]:
        if query == _NO_RESULTS_QUERY:
            return []
        return [
            (
                Document(
                    page_content=f"facts about {query}", metadata={"source_id": query}
                ),
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


class _Chat:
    def __init__(self, model: _ScriptedChatModel):
        search_tool = build_search_tool(cast(RetrievalService, _StubRetrievalService()))
        self.graph: CompiledStateGraph = build_graph(
            model, [search_tool], InMemorySaver()
        )
        self.config: RunnableConfig = {"configurable": {"thread_id": "t1"}}

    async def send(self, text: str) -> list[StreamEvent]:
        return [
            event
            async for event in stream_events(
                self.graph, [HumanMessage(content=text)], self.config
            )
        ]

    async def saved_messages(self) -> list[BaseMessage]:
        return (await self.graph.aget_state(self.config)).values["messages"]


def _sources(events: list[StreamEvent]) -> list[str]:
    return [
        source for e in events if isinstance(e, SourcesReady) for source in e.sources
    ]


def _text(events: list[StreamEvent]) -> str:
    return "".join(e.text for e in events if isinstance(e, TextDelta))


def _is_revision_call(call: dict[str, Any]) -> bool:
    return call["messages"][-1].content == REVISION_INSTRUCTION


async def test_streams_only_the_agents_answer_not_the_guards_verdicts() -> None:
    model = _ScriptedChatModel(answers=[_search("pricing"), _answer("It costs 10.")])

    events = await _Chat(model).send("How much?")

    assert _text(events) == "It costs 10."


async def test_sources_cover_only_the_current_turn() -> None:
    model = _ScriptedChatModel(
        answers=[_search("pricing"), _answer("A"), _search("security"), _answer("B")]
    )
    chat = _Chat(model)

    assert _sources(await chat.send("first")) == ["pricing"]
    assert _sources(await chat.send("second")) == ["security"]


async def test_a_search_that_finds_nothing_sends_empty_sources() -> None:
    model = _ScriptedChatModel(
        answers=[_search(_NO_RESULTS_QUERY), _answer("I don't know.")]
    )

    events = await _Chat(model).send("first")

    assert [e for e in events if isinstance(e, SourcesReady)] == [
        SourcesReady(sources=[])
    ]


async def test_a_turn_without_a_search_sends_no_sources() -> None:
    model = _ScriptedChatModel(answers=[_answer("hi!")])

    events = await _Chat(model).send("hello")

    assert not any(isinstance(e, SourcesReady) for e in events)


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

    # MAX_REVISIONS is 1: one revision, and the revised answer isn't re-verified.
    assert sum(_is_revision_call(call) for call in model.agent_calls) == 1
    assert len(model.verifier_calls) == 1
    assert _text(events).endswith("still wrong")


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
    assert OFF_TOPIC_INSTRUCTION in off_topic_call["messages"][0].content
    assert off_topic_call["tools"] == []
    assert OFF_TOPIC_INSTRUCTION not in on_topic_call["messages"][0].content
    assert on_topic_call["tools"] == ["search_kb"]
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


async def test_history_shows_each_question_with_its_final_answer_and_sources() -> None:
    model = _ScriptedChatModel(
        answers=[
            _search("pricing"),
            _answer("wrong"),
            _answer("revised"),
            _answer("You're welcome!"),
            _search(_NO_RESULTS_QUERY),
            _answer("I don't know."),
        ],
        groundedness_verdicts=["UNGROUNDED"],
    )
    chat = _Chat(model)
    await chat.send("How much?")
    await chat.send("thanks")
    await chat.send("Who won the cup?")

    history = to_history(await chat.saved_messages())

    assert [(m.role, m.text, m.sources) for m in history] == [
        ("user", "How much?", None),
        ("assistant", "revised", ["pricing"]),  # the rejected draft is dropped
        ("user", "thanks", None),
        ("assistant", "You're welcome!", None),  # didn't search
        ("user", "Who won the cup?", None),
        ("assistant", "I don't know.", []),  # searched, found nothing
    ]


def test_history_of_an_empty_or_missing_thread_is_empty() -> None:
    # A thread the checkpointer doesn't have (e.g. a conversation whose messages were
    # never saved) reads back as no messages; that used to crash with a zip() ValueError.
    assert to_history([]) == []
