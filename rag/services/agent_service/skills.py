import re
import uuid

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool

from rag.domain.models import SKILL_NAME_PATTERN, RunContext, SkillContent
from rag.domain.ports import SkillsPort
from rag.services.agent_service.prompts import SKILL_FILES_NOTE

# The tools that hand the model a skill's instructions and its reference files: not
# knowledge-base content, so the groundedness guard leaves their results out.
SKILL_TOOL = "load_skill"
SKILL_FILE_TOOL = "read_skill_file"
SKILL_TOOLS = frozenset({SKILL_TOOL, SKILL_FILE_TOOL})

# A message that invokes a skill starts with "/<name>", then a space or its end.
_INVOCATION = re.compile(rf"/({SKILL_NAME_PATTERN})(?=\s|$)")


def loaded_skill(content: SkillContent) -> str:
    """What loading a skill hands the model: its instructions, then the paths of its
    reference files, if it has any.
    """
    if not content.files:
        return content.instructions
    files = "\n".join(f"- {path}" for path in content.files)
    return f"{content.instructions}\n\n{SKILL_FILES_NOTE.format(files=files)}"


def skill_tool(skills: SkillsPort) -> BaseTool:
    """load_skill: the instructions of one of the user's skills, by name. The user is
    the turn's, from its RunContext; the model only names the skill.
    """

    @tool(
        SKILL_TOOL,
        description=(
            "Load the instructions of one of the user's skills, by its name, before "
            "answering a request that fits the skill's description."
        ),
    )
    async def load_skill(name: str, runtime: ToolRuntime[RunContext]) -> str:
        content = await skills.content(runtime.context.user_id, name)
        if content is None:
            return f"The user has no skill named {name!r}."
        return loaded_skill(content)

    return load_skill


def skill_file_tool(skills: SkillsPort) -> BaseTool:
    """read_skill_file: one reference file of one of the user's skills, by the skill's
    name and the file's path, as load_skill listed it. The user is the turn's, from its
    RunContext.
    """

    @tool(
        SKILL_FILE_TOOL,
        description=(
            "Read a reference file of one of the user's skills, by the skill's name "
            "and the file's path as load_skill listed it."
        ),
    )
    async def read_skill_file(
        skill: str, path: str, runtime: ToolRuntime[RunContext]
    ) -> str:
        content = await skills.file(runtime.context.user_id, skill, path)
        if content is None:
            return f"The user's skill {skill!r} has no file {path!r}."
        return content

    return read_skill_file


def invoked_skill(text: str) -> str | None:
    """The name of the skill the message invokes ("/<name> ..."), whether or not the
    user has one of that name; None if it invokes none.
    """
    match = _INVOCATION.match(text.lstrip())
    return match.group(1) if match else None


def skill_loaded(name: str, instructions: str) -> list[BaseMessage]:
    """The load_skill call and its result (`instructions`, as `loaded_skill` words
    them), as if the model had made it: what a turn that invokes the skill starts
    with, so the model follows it, and later turns remember it was loaded.
    """
    call_id = f"call_{uuid.uuid4().hex}"  # shaped like the ids OpenAI gives calls
    return [
        AIMessage(
            content="",
            tool_calls=[{"name": SKILL_TOOL, "args": {"name": name}, "id": call_id}],
        ),
        ToolMessage(content=instructions, name=SKILL_TOOL, tool_call_id=call_id),
    ]
