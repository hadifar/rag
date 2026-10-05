import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

from rag.domain.models.agent.artifact import Artifact
from rag.domain.models.agent.middleware import Middleware


@dataclass(frozen=True)
class RunContext:
    """Who a chat turn is for, and where: given to the agent's every tool and
    middleware for that turn.
    """

    user_id: uuid.UUID
    conversation_id: uuid.UUID


@dataclass(frozen=True)
class ToolResult:
    content: str  # what the model reads
    # What the user is handed beside it (e.g. the knowledge-base sources the content
    # came from), sent as the turn's artifacts; None for a tool that hands over nothing.
    artifacts: list[Artifact] | None = None


# "product": works on what the agent is about (e.g. searching the knowledge base).
# "user": acts on the user instead (e.g. saving a preference), so it stays available
# off-topic, and its results aren't context an answer is checked against.
ToolKind = Literal["product", "user"]


@dataclass(frozen=True)
class Tool:
    """A tool for an agent, free of any framework: the agent service wraps it."""

    name: str  # what the model calls it; unique among an agent's tools
    description: str  # what the model is told it does
    run: Callable[[str, RunContext], Awaitable[ToolResult]]  # the model's argument in
    kind: ToolKind = "product"
    parameter: str = "query"  # the name the model gives its one argument


@dataclass(frozen=True)
class Capability:
    """What a feature outside the agent service gives an agent (e.g. the user's
    preferences): more tools, and instructions read fresh for each model call of a
    turn, so a change one tool call makes applies from the next call on. The
    instructions are added to the call only, never saved to the thread.
    """

    tools: list[Tool] = field(default_factory=list[Tool])
    instructions: Callable[[RunContext], Awaitable[str | None]] | None = None


@dataclass(frozen=True)
class ToolAgentSpec:
    """The standard tool-calling agent: the model calls `tools` until it answers."""

    system_prompt: str
    tools: list[Tool]
    # Wrapped around each model call in this order, the first outermost.
    middleware: list[Middleware] = field(default_factory=list[Middleware])
    # Their tools join `tools`; their instructions follow the middleware's.
    capabilities: list[Capability] = field(default_factory=list[Capability])
