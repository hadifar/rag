from collections.abc import Sequence
from itertools import pairwise
from typing import TypeGuard

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from rag.domain.models import HistoryMessage

# Guards inject their instructions per model call instead of saving them to the
# thread, so every HumanMessage in state is the user's and marks the start of a turn.


def is_final_answer(message: BaseMessage | None) -> TypeGuard[AIMessage]:
    """An answer to the user, as opposed to a model call that asks for tools."""
    return isinstance(message, AIMessage) and not message.tool_calls


def current_turn(messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """The messages from the user's latest message onward."""
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index:]
    return messages


def turn_tool_messages(messages: Sequence[BaseMessage]) -> list[ToolMessage]:
    return [m for m in current_turn(messages) if isinstance(m, ToolMessage)]


def turn_sources(messages: Sequence[BaseMessage]) -> list[str] | None:
    """Deduplicated source ids search_kb attached (as its artifact) this turn; empty if
    it searched and found nothing, None if it didn't search at all.
    """
    return _sources(current_turn(messages))


def to_history(messages: Sequence[BaseMessage]) -> list[HistoryMessage]:
    """The thread as the user saw it: each question, then that turn's final answer
    with its sources. Tool calls are left out, and if the answer was revised only
    the revision is kept.
    """
    history: list[HistoryMessage] = []
    for turn in _split_turns(messages):
        history.append(HistoryMessage(role="user", text=turn[0].text))
        answers = [m for m in turn if is_final_answer(m) and m.text]
        if answers:
            history.append(
                HistoryMessage(
                    role="assistant", text=answers[-1].text, sources=_sources(turn)
                )
            )
    return history


def _split_turns(messages: Sequence[BaseMessage]) -> list[Sequence[BaseMessage]]:
    """Each turn runs from one HumanMessage up to the next; none for an empty thread."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return [messages[start:end] for start, end in pairwise([*starts, len(messages)])]


def _sources(turn: Sequence[BaseMessage]) -> list[str] | None:
    artifacts = [
        message.artifact
        for message in turn
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list)
    ]
    if not artifacts:
        return None
    return sorted({source for artifact in artifacts for source in artifact})
