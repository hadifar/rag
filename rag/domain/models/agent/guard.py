from typing import Literal

from pydantic import BaseModel, Field

# allow: about the product. off_topic: harmless but unrelated, so the model declines.
# block: an injection, jailbreak or harmful request, which never reaches the model.
InputDecision = Literal["allow", "off_topic", "block"]


class InputVerdict(BaseModel):
    """The input guard's verdict on a user message: the schema its LLM call fills,
    and what its cache keeps.
    """

    # Before the decision, so the model gives its reason before it decides.
    reason: str = Field(
        description="One sentence on why the message gets the decision."
    )
    decision: InputDecision


class AnswerVerdict(BaseModel):
    """The answer guard's verdict on an answer: the schema its LLM call fills."""

    grounded: bool
