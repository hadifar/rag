from typing import Any

from langchain.agents.middleware.todo import write_todos
from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from rag.domain.models import ARTIFACTS, RunContext, SkillContent, SourceArtifact
from rag.domain.ports import SearchPort, SkillsPort
from rag.services.agent_service.prompts import SKILL_FILES_NOTE

# The tools that hand the model a skill's instructions and its reference files: not
# knowledge-base content, so the answer guard leaves their results out.
SKILL_TOOL = "load_skill"
SKILL_FILE_TOOL = "read_skill_file"
SKILL_TOOLS = frozenset({SKILL_TOOL, SKILL_FILE_TOOL})


def agent_tools(search: SearchPort, skills: SkillsPort) -> list[BaseTool]:
    """Every tool the chat agent's model can call."""
    return [
        search_tool(search),
        skill_tool(skills),
        skill_file_tool(skills),
        write_todos,
    ]


def search_tool(knowledge_base: SearchPort) -> BaseTool:
    """search_kb: the passages the knowledge base finds, each tagged with its source
    id. The sources ride along as the ToolMessage's artifact, as plain JSON the agent's
    memory of the turn saves as is; the turn hands them to the user.
    """

    @tool(
        "search_kb",
        description="Search the AtlasFlow knowledge base for relevant documentation.",
        response_format="content_and_artifact",
    )
    async def search_kb(query: str) -> tuple[str, list[dict[str, Any]]]:
        results = await knowledge_base.search(query)
        if not results:
            return "No relevant documentation found.", []

        documents = [doc for doc, _score in results]
        content = "\n\n".join(
            f"[source: {doc.metadata['source_id']}]\n{doc.text}" for doc in documents
        )
        sources = [
            SourceArtifact(id=str(doc.metadata["source_id"])) for doc in documents
        ]
        return content, ARTIFACTS.dump_python(sources, mode="json")

    return search_kb


def render_skill(content: SkillContent) -> str:
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
        return render_skill(content)

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
