import re
import uuid

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from rag.domain.models import SKILL_NAME_PATTERN
from rag.services.agent_service.tools import SKILL_TOOL

# A message that invokes a skill starts with "/<name>", then a space or its end.
_INVOCATION = re.compile(rf"/({SKILL_NAME_PATTERN})(?=\s|$)")


def invoked_skill(text: str) -> str | None:
    """The name of the skill the message invokes ("/<name> ..."), whether or not the
    user has one of that name; None if it invokes none.
    """
    match = _INVOCATION.match(text.lstrip())
    return match.group(1) if match else None


def skill_loaded(name: str, instructions: str) -> list[BaseMessage]:
    """The load_skill call and its result, as if the model had made it: what a turn
    that invokes the skill starts with, so the model follows it, and later turns
    remember it was loaded.
    """
    call_id = f"call_{uuid.uuid4().hex}"  # shaped like the ids OpenAI gives calls
    return [
        AIMessage(
            content="",
            tool_calls=[{"name": SKILL_TOOL, "args": {"name": name}, "id": call_id}],
        ),
        ToolMessage(content=instructions, name=SKILL_TOOL, tool_call_id=call_id),
    ]
