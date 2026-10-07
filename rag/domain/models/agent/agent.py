import uuid
from dataclasses import dataclass
from typing import Any, Literal, get_args

# The chat models a user picks from: each is the model (for Azure, the deployment) the
# provider is called with.
ModelName = Literal["gpt-6-luna", "gpt-6-astra", "gpt-6-sol"]
MODEL_NAMES: tuple[ModelName, ...] = get_args(ModelName)
DEFAULT_MODEL: ModelName = "gpt-6-luna"

# How hard a reasoning model thinks, as the user picks it.
Effort = Literal["low", "medium", "max"]
EFFORTS: tuple[Effort, ...] = get_args(Effort)
DEFAULT_EFFORT: Effort = "low"


@dataclass(frozen=True)
class RunContext:
    """Who a chat turn is for, and where: the turn's trace is tagged with it. And
    how it runs: the model and effort its conversation is set to.
    """

    user_id: uuid.UUID
    conversation_id: uuid.UUID
    model: ModelName = DEFAULT_MODEL
    effort: Effort = DEFAULT_EFFORT


# What the agent remembers of one turn: its own messages (the question, its tool calls
# and their results, its answers) as JSON that only the agent service reads.
AgentMemory = list[dict[str, Any]]
