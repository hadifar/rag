from typing import Annotated, Literal

from pydantic import Field, TypeAdapter
from pydantic.dataclasses import dataclass

# What a tool hands the user beside what the model reads, told apart by `kind`.


@dataclass(frozen=True)
class SourceArtifact:
    """A knowledge-base source the answer drew on, by its id."""

    id: str
    kind: Literal["source"] = "source"


# A new kind joins the union here.
Artifact = Annotated[SourceArtifact, Field(discriminator="kind")]

# A list of artifacts to and from plain JSON, as a ToolMessage carries them.
ARTIFACTS = TypeAdapter(list[Artifact])
