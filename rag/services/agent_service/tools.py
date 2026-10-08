from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool
from rag.domain.models import ARTIFACTS, SourceArtifact
from rag.domain.ports import SearchPort

# The skill tools are in skills.py, with the rest of the skills' handling.


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
