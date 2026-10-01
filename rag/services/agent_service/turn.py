from collections.abc import Sequence
from itertools import pairwise
from typing import TypeGuard

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from rag.domain.models import (
    AssistantMessage,
    HistoryMessage,
    ReferencesReady,
    UserMessage,
)
from rag.services.agent_service.streaming import replay

# Guards inject their instructions per model call instead of saving them to the
# thread, so every HumanMessage in state is the user's and marks the start of a turn.
# TODO: we must refactor this


def is_final_answer(message: BaseMessage | None) -> TypeGuard[AIMessage]:
    """An answer to the user, as opposed to a model call that asks for tools."""
    return isinstance(message, AIMessage) and not message.tool_calls


def current_turn(messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """The messages from the user's latest message onward."""
    turns = _split_turns(messages)
    return turns[-1] if turns else messages


def turn_tool_messages(messages: Sequence[BaseMessage]) -> list[ToolMessage]:
    return [m for m in current_turn(messages) if isinstance(m, ToolMessage)]


def turn_references(messages: Sequence[BaseMessage]) -> list[str] | None:
    """Deduplicated ids the tools cited (as their artifacts) this turn; empty if
    they found nothing, None if no citing tool ran.
    """
    return _references(current_turn(messages))


def to_history(messages: Sequence[BaseMessage]) -> list[HistoryMessage]:
    """The thread as the user saw it: each question, then the events its answer
    streamed (reasoning, searches, the plan, the answer) and its references. If the
    answer was revised, the rejected drafts are left out.
    """
    history: list[HistoryMessage] = []
    for turn in _split_turns(messages):
        history.append(UserMessage(text=turn[0].text))
        answers = [m for m in turn if is_final_answer(m)]
        rejected = {id(m) for m in answers[:-1]}
        events = replay([m for m in turn[1:] if id(m) not in rejected])
        references = _references(turn)
        if references is not None:
            events.append(ReferencesReady(references=references))
        if events:
            history.append(AssistantMessage(events=events))
    return history


def _split_turns(messages: Sequence[BaseMessage]) -> list[Sequence[BaseMessage]]:
    """Each turn runs from one HumanMessage up to the next; none for an empty thread."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return [messages[start:end] for start, end in pairwise([*starts, len(messages)])]


def _references(turn: Sequence[BaseMessage]) -> list[str] | None:
    artifacts = [
        message.artifact
        for message in turn
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list)
    ]
    if not artifacts:
        return None
    return sorted({ref for artifact in artifacts for ref in artifact})
