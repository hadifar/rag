from dataclasses import dataclass, field
from typing import Protocol


class ToolPort(Protocol):
    """A tool an agent may call. Opaque outside the agent service, which builds it."""

    @property
    def name(self) -> str: ...


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


Check = OffTopicCheck | GroundednessCheck


@dataclass(frozen=True)
class Planning:
    """Lets the agent split a multi-part question into steps and work through them
    before answering. The plan is its private scratchpad, never part of the answer.
    """

    instructions: str  # when to plan and how, for this agent's kind of work


@dataclass(frozen=True)
class ToolAgentSpec:
    """The standard tool-calling agent: the model calls `tools` until it answers."""

    system_prompt: str
    tools: list[ToolPort]
    checks: list[Check] = field(default_factory=list[Check])  # run in this order
    planning: Planning | None = None


# Every kind of agent the agent service can build; a custom graph adds its spec here.
AgentSpec = ToolAgentSpec
