from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
    messages_from_dict,
    messages_to_dict,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately

from rag.domain.models import ARTIFACTS, AgentMemory, Artifact, ArtifactsReady
from rag.services.agent_service.messages import split_turns
from rag.services.agent_service.skills import SKILL_TOOL

# The agent's memory of a conversation: what each turn saves (`remember`), and how
# much of it later turns reread (`recall`).


@dataclass(frozen=True)
class HistoryLimits:
    """How much of the earlier turns the model rereads: past either limit, the oldest
    turns are left out.
    """

    max_tokens: int = 16_000  # counted approximately
    max_turns: int = 20


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


def recall(history: Sequence[AgentMemory], limits: HistoryLimits) -> list[AnyMessage]:
    """The earlier turns as the model is to read them: each compacted (`_compact`),
    then the oldest dropped, whole turns at a time, until the rest are within
    `limits` (attachments, read afresh per call, aren't counted). The saved memory
    stays whole, so the limits can change without losing anything.
    """
    # Not history[-max_turns:]: [-0:] would keep them all.
    recent = history[max(0, len(history) - limits.max_turns) :]
    messages = [m for turn in recent for m in messages_from_dict(turn)]
    compacted = [m for turn in split_turns(messages) for m in _compact(turn)]
    kept = trim_messages(
        compacted,
        max_tokens=limits.max_tokens,
        token_counter=count_tokens_approximately,
        strategy="last",
        start_on="human",  # a cut inside a turn drops the rest of it too
    )
    return cast(list[AnyMessage], kept)


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


def _compact(turn: Sequence[BaseMessage]) -> list[BaseMessage]:
    """The turn's question, its skill loads and its final answer: its searches and
    reads of skill reference files are left out, since a later turn can do them again.
    A skill load stays so a follow-up still follows the skill.
    """
    loads = {
        call["id"]
        for m in turn
        if isinstance(m, AIMessage) and _only_loads_skills(m)
        for call in m.tool_calls
    }
    return [
        m
        for m in turn
        if isinstance(m, HumanMessage)
        or (isinstance(m, AIMessage) and (not m.tool_calls or _only_loads_skills(m)))
        or (isinstance(m, ToolMessage) and m.tool_call_id in loads)
    ]


def _only_loads_skills(message: AIMessage) -> bool:
    return bool(message.tool_calls) and all(
        call["name"] == SKILL_TOOL for call in message.tool_calls
    )
