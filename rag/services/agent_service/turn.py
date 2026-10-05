from collections.abc import Sequence
from itertools import pairwise
from typing import TypeGuard

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from pydantic import TypeAdapter

from rag.domain.models import Artifact

_ARTIFACTS = TypeAdapter(list[Artifact])

# Guards inject their instructions per model call instead of saving them to the
# thread, so every HumanMessage in state is the user's and marks the start of a turn.


def is_final_answer(message: BaseMessage | None) -> TypeGuard[AIMessage]:
    """An answer to the user, as opposed to a model call that asks for tools."""
    return isinstance(message, AIMessage) and not message.tool_calls


def current_turn(messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """The messages from the user's latest message onward."""
    turns = split_turns(messages)
    return turns[-1] if turns else messages


def turn_tool_messages(messages: Sequence[BaseMessage]) -> list[ToolMessage]:
    return [m for m in current_turn(messages) if isinstance(m, ToolMessage)]


def turn_artifacts(messages: Sequence[BaseMessage]) -> list[Artifact] | None:
    """What the tools handed the user this turn, deduplicated in the order they did;
    empty if they found nothing, None if no tool that hands anything over ran.
    """
    return _artifacts(current_turn(messages))


def split_turns(messages: Sequence[BaseMessage]) -> list[Sequence[BaseMessage]]:
    """Each turn runs from one HumanMessage up to the next; none for an empty thread."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return [messages[start:end] for start, end in pairwise([*starts, len(messages)])]


def _artifacts(turn: Sequence[BaseMessage]) -> list[Artifact] | None:
    handed_over = [
        message.artifact
        for message in turn
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list)
    ]
    if not handed_over:
        return None
    artifacts = _ARTIFACTS.validate_python([a for each in handed_over for a in each])
    return list(dict.fromkeys(artifacts))
