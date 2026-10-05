from typing import Any

from langchain.agents.middleware import ModelRequest
from langchain_core.messages import SystemMessage


def with_instructions(request: ModelRequest[Any], *texts: str) -> ModelRequest[Any]:
    """`request` with `texts` appended to its system message, for this model call only:
    never saved to the thread, so they can't leak into later turns.
    """
    base = request.system_message.text if request.system_message else ""
    return request.override(
        system_message=SystemMessage(content="\n\n".join([base, *texts]))
    )
