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
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately

from rag.domain.models import AgentMemory
from rag.services.agent_service.tools import SKILL_TOOL
from rag.services.agent_service.turn import split_turns


@dataclass(frozen=True)
class HistoryLimits:
    """How much of the earlier turns the model rereads: past either limit, the oldest
    turns are left out.
    """

    max_tokens: int = 16_000  # counted approximately
    max_turns: int = 20


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
