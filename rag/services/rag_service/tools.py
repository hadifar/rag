from rag.domain.agents import Tool, ToolResult
from rag.domain.ports import SearchPort


def search_tool(knowledge_base: SearchPort) -> Tool:
    """search_kb: the passages the knowledge base finds, each tagged with its source
    id, which the turn cites as its references.
    """

    async def search(query: str) -> ToolResult:
        results = await knowledge_base.search(query)
        if not results:
            return ToolResult("No relevant documentation found.", references=[])

        documents = [doc for doc, _score in results]
        content = "\n\n".join(
            f"[source: {doc.metadata['source_id']}]\n{doc.text}" for doc in documents
        )
        return ToolResult(
            content, references=[str(doc.metadata["source_id"]) for doc in documents]
        )

    return Tool(
        name="search_kb",
        description="Search the AtlasFlow knowledge base for relevant documentation.",
        run=search,
    )
