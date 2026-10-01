from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from rag.domain.models.agent.middleware import Middleware


@dataclass(frozen=True)
class ToolResult:
    content: str  # what the model reads
    # What the content came from (e.g. knowledge-base source ids), sent to the user as
    # the turn's references; None for a tool that cites nothing.
    references: list[str] | None = None


@dataclass(frozen=True)
class Tool:
    """A tool for an agent, free of any framework: the agent service wraps it."""

    name: str  # what the model calls it; unique among an agent's tools
    description: str  # what the model is told it does
    run: Callable[[str], Awaitable[ToolResult]]  # the model's query in


@dataclass(frozen=True)
class ToolAgentSpec:
    """The standard tool-calling agent: the model calls `tools` until it answers."""

    system_prompt: str
    tools: list[Tool]
    # Wrapped around each model call in this order, the first outermost.
    middleware: list[Middleware] = field(default_factory=list[Middleware])


# # Every kind of agent the agent service can build;
AgentSpec = ToolAgentSpec


MAX_PREFERENCES = 20  # per user; every one is added to each of their chat turns' prompt
MAX_PREFERENCE_LENGTH = 200


@dataclass(frozen=True)
class Preference:
    """Something the user wants of every answer (e.g. "Answer in Dutch"), in their own
    words. Kept per user, across all their conversations.
    """

    id: str
    text: str
