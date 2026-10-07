from typing import Any

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from rag.domain.models import ARTIFACTS, RunContext, SourceArtifact
from rag.domain.ports import SearchPort, SkillsPort

# The tool that hands the model a skill's instructions: not knowledge-base content, so
# the groundedness guard leaves its results out.
SKILL_TOOL = "load_skill"


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
        instructions = await skills.instructions(runtime.context.user_id, name)
        if instructions is None:
            return f"The user has no skill named {name!r}."
        return instructions

    return load_skill
