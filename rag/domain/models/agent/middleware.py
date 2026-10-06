from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class OffTopicMiddleware:
    """Classifies each user message, with the turns before it: a blocked one (an
    injection, jailbreak or harmful request) gets a fixed refusal and never reaches the
    model; for an off-topic one the agent is told to decline and gets no tools.
    """

    scope: str  # what the agent answers about, as the classifier is told
    decline_instruction: str  # added to the model call for an off-topic message
    refusal: str  # sent instead of an answer for a blocked message


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
