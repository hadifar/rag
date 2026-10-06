from collections.abc import Sequence
from itertools import pairwise
from typing import TypeGuard

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
    messages_to_dict,
)
from rag.domain.models import ARTIFACTS, AgentMemory, Artifact, ArtifactsReady

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


def remember(
    messages: Sequence[BaseMessage], question: HumanMessage
) -> tuple[AgentMemory | None, ArtifactsReady | None]:
    """What the agent is to remember of the turn `question` started (its messages, from
    the question on), and what its tools handed the user, if any tool that hands
    anything over ran; neither if the question was dropped (a blocked one).
    """
    ids = [m.id for m in messages]
    if question.id not in ids:
        return None, None
    turn = messages[ids.index(question.id) :]
    artifacts = _artifacts(turn)
    handed_over = None if artifacts is None else ArtifactsReady(artifacts=artifacts)
    return messages_to_dict(turn), handed_over


def split_turns(messages: Sequence[BaseMessage]) -> list[Sequence[BaseMessage]]:
    """Each turn runs from one HumanMessage up to the next; none for an empty thread."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return [messages[start:end] for start, end in pairwise([*starts, len(messages)])]


def _artifacts(turn: Sequence[BaseMessage]) -> list[Artifact] | None:
    """What the tools handed the user in `turn`, deduplicated in the order they did;
    empty if they found nothing, None if no tool that hands anything over ran.
    """
    handed_over = [
        message.artifact
        for message in turn
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list)
    ]
    if not handed_over:
        return None
    artifacts = ARTIFACTS.validate_python([a for each in handed_over for a in each])
    return list(dict.fromkeys(artifacts))
