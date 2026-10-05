from rag.domain.models import RunContext, SourceArtifact, Tool, ToolResult
from rag.domain.ports import SearchPort


def search_tool(knowledge_base: SearchPort) -> Tool:
    """search_kb: the passages the knowledge base finds, each tagged with its source
    id, which the turn hands the user as its sources. The knowledge base is the same for
    every user, so the turn's context isn't used.
    """

    async def search(query: str, _ctx: RunContext) -> ToolResult:
        results = await knowledge_base.search(query)
        if not results:
            return ToolResult("No relevant documentation found.", artifacts=[])

        documents = [doc for doc, _score in results]
        content = "\n\n".join(
            f"[source: {doc.metadata['source_id']}]\n{doc.text}" for doc in documents
        )
        sources = [
            SourceArtifact(id=str(doc.metadata["source_id"])) for doc in documents
        ]
        return ToolResult(content, artifacts=sources)

    return Tool(
        name="search_kb",
        description="Search the AtlasFlow knowledge base for relevant documentation.",
        run=search,
    )
