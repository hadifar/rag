"""Drives the real generation graph with a scripted fake LLM and an in-memory
checkpointer, so multi-turn behavior (what carries over between turns in one
thread) is tested without any external service.
"""

import uuid
from typing import Any, cast

import pytest
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import Field

from rag.domain.events import SourcesReady, StreamEvent
from rag.services.generation_service.guards.groundness import REVISION_INSTRUCTION
from rag.services.generation_service.guards.topical import OFF_TOPIC_INSTRUCTION
from rag.services.generation_service.service import GenerationService
from rag.services.retrieval_service.service import RetrievalService


class _ScriptedChatModel(BaseChatModel):
    """Answers the guardrail and verifier prompts from their verdict scripts and
    every other call (the agent) from `agent_replies`, recording what each saw.
    """

    relevance_verdicts: list[str] = Field(default_factory=list)
    grounding_verdicts: list[str] = Field(default_factory=list)
    agent_replies: list[AIMessage] = Field(default_factory=list)
    agent_calls: list[list[BaseMessage]] = Field(default_factory=list)
    verifier_prompts: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "_ScriptedChatModel":  # pyright: ignore[reportIncompatibleMethodOverride]
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])

    def _reply(self, messages: list[BaseMessage]) -> AIMessage:
        prompt = str(messages[0].content)
        if prompt.startswith("You are a scope classifier"):
            return AIMessage(content=self.relevance_verdicts.pop(0))
        if prompt.startswith("You are a strict fact-checker"):
            self.verifier_prompts.append(prompt)
            return AIMessage(content=self.grounding_verdicts.pop(0))
        self.agent_calls.append(messages)
        return self.agent_replies.pop(0)


class _StubRetrievalService:
    async def search(self, query: str, top_k: int = 3) -> list[tuple[Document, float]]:
        document = Document(
            page_content=f"about {query}", metadata={"source_id": f"{query}.md"}
        )
        return [(document, 1.0)]


def _search(query: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "search_kb", "args": {"query": query}, "id": str(uuid.uuid4())}
        ],
    )


def _answer(text: str) -> AIMessage:
    return AIMessage(content=text)


def _grounded_turn(llm: _ScriptedChatModel, query: str) -> None:
    """Scripts one on-topic turn: search `query`, answer, pass verification."""
    llm.relevance_verdicts.append("RELEVANT")
    llm.agent_replies += [_search(query), _answer(f"answer about {query}")]
    llm.grounding_verdicts.append("GROUNDED")


@pytest.fixture
def llm() -> _ScriptedChatModel:
    return _ScriptedChatModel()


@pytest.fixture
def chat(llm: _ScriptedChatModel):
    service = GenerationService(
        llm=llm,
        ranking_service=cast(RetrievalService, _StubRetrievalService()),
        checkpointer=InMemorySaver(),
    )
    thread_id = str(uuid.uuid4())

    async def send(message: str) -> list[StreamEvent]:
        return [event async for event in service.stream_chat(message, thread_id)]

    return send


def _sources(events: list[StreamEvent]) -> list[str]:
    return next((e.sources for e in events if isinstance(e, SourcesReady)), [])


async def test_sources_only_cover_the_current_turn(llm, chat) -> None:
    _grounded_turn(llm, "alpha")
    _grounded_turn(llm, "beta")

    first = await chat("tell me about alpha")
    second = await chat("tell me about beta")

    assert _sources(first) == ["alpha.md"]
    assert _sources(second) == ["beta.md"]


def _revised_turn(llm: _ScriptedChatModel, query: str) -> None:
    """Scripts one on-topic turn whose first answer fails verification once."""
    llm.relevance_verdicts.append("RELEVANT")
    llm.agent_replies += [_search(query), _answer("unsupported"), _answer("revised")]
    llm.grounding_verdicts += ["UNGROUNDED", "GROUNDED"]


async def test_each_turn_gets_its_own_revision_attempt(llm, chat) -> None:
    _revised_turn(llm, "alpha")
    _revised_turn(llm, "beta")

    await chat("tell me about alpha")
    await chat("tell me about beta")

    # 3 agent calls per turn: search, the ungrounded answer, and the revision.
    assert len(llm.agent_calls) == 6
    assert llm.grounding_verdicts == []


def _saw(call: list[BaseMessage], instruction: str) -> bool:
    return any(message.content == instruction for message in call)


async def test_off_topic_instruction_does_not_outlive_its_turn(llm, chat) -> None:
    llm.relevance_verdicts.append("IRRELEVANT")
    llm.agent_replies.append(_answer("I can only help with AtlasFlow."))
    _grounded_turn(llm, "beta")

    await chat("what's the weather?")
    await chat("tell me about beta")

    off_topic_call, *next_turn_calls = llm.agent_calls
    assert _saw(off_topic_call, OFF_TOPIC_INSTRUCTION)
    assert not any(_saw(call, OFF_TOPIC_INSTRUCTION) for call in next_turn_calls)


async def test_revision_instruction_does_not_outlive_its_turn(llm, chat) -> None:
    _revised_turn(llm, "alpha")
    _grounded_turn(llm, "beta")

    await chat("tell me about alpha")
    await chat("tell me about beta")

    revision_call = llm.agent_calls[2]
    next_turn_calls = llm.agent_calls[3:]
    assert _saw(revision_call, REVISION_INSTRUCTION)
    assert not any(_saw(call, REVISION_INSTRUCTION) for call in next_turn_calls)


async def test_verifier_only_sees_the_current_turns_context(llm, chat) -> None:
    _grounded_turn(llm, "alpha")
    _grounded_turn(llm, "beta")

    await chat("tell me about alpha")
    await chat("tell me about beta")

    second_turn_prompt = llm.verifier_prompts[1]
    assert "about beta" in second_turn_prompt
    assert "about alpha" not in second_turn_prompt


async def test_turn_without_retrieval_skips_verification(llm, chat) -> None:
    _grounded_turn(llm, "alpha")
    llm.relevance_verdicts.append("RELEVANT")
    llm.agent_replies.append(_answer("You're welcome!"))

    await chat("tell me about alpha")
    await chat("thanks")

    assert len(llm.verifier_prompts) == 1
