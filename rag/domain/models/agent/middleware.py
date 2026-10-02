from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class OffTopicMiddleware:
    """Classifies each user message; for an off-topic one the agent is told to decline
    and gets no tools.
    """


@dataclass(frozen=True)
class GroundednessMiddleware:
    """Checks each final answer against the turn's tool results; an unsupported one is
    sent back to revise, up to `max_revisions` times per turn.
    """

    max_revisions: int


@dataclass(frozen=True)
class TodolistMiddleware:
    """Lets the agent split a multi-part question into steps and work through them
    before answering. The plan is its private scratchpad, never part of the answer.
    """

    instructions: str  # when to plan and how, for this agent's kind of work


Middleware = OffTopicMiddleware | GroundednessMiddleware | TodolistMiddleware
