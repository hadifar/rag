import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunContext:
    """Who a chat turn is for, and where: given to the agent's every tool and
    middleware for that turn.
    """

    user_id: uuid.UUID
    conversation_id: uuid.UUID


# What the agent remembers of one turn: its own messages (the question, its tool calls
# and their results, its answers) as JSON that only the agent service reads.
AgentMemory = list[dict[str, Any]]
