from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal


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
class OffTopicCheck:
    """Classifies each user message; for an off-topic one the agent is told to decline
    and gets no tools.
    """


@dataclass(frozen=True)
class GroundednessCheck:
    """Checks each final answer against the turn's tool results; an unsupported one is
    sent back to revise, up to `max_revisions` times per turn.
    """

    max_revisions: int


@dataclass(frozen=True)
class Planning:
    """Lets the agent split a multi-part question into steps and work through them
    before answering. The plan is its private scratchpad, never part of the answer.
    """

    instructions: str  # when to plan and how, for this agent's kind of work


@dataclass(frozen=True)
class RememberPreferences:
    """Answers by the user's preferences, and saves or forgets one when they ask."""


Middleware = OffTopicCheck | GroundednessCheck | Planning | RememberPreferences


@dataclass(frozen=True)
class ToolAgentSpec:
    """The standard tool-calling agent: the model calls `tools` until it answers."""

    system_prompt: str
    tools: list[Tool]
    # Wrapped around each model call in this order, the first outermost.
    middleware: list[Middleware] = field(default_factory=list[Middleware])


# Every kind of agent the agent service can build; a custom graph adds its spec here.
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


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCall:
    name: str
    status: Literal["pending", "done"]
    query: str | None = None
    output: str | None = None


@dataclass
class ReferencesReady:
    """What the turn's tools cited (e.g. knowledge-base source ids), deduplicated; sent
    once the turn is done, and only if a tool that cites anything ran.
    """

    references: list[str]


StreamEvent = TextDelta | ToolCall | ReferencesReady
