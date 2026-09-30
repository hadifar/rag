from langchain_core.tools import BaseTool, tool

from rag.domain.ports import SearchPort


def build_search_tool(knowledge_base: SearchPort) -> BaseTool:

    @tool(response_format="content_and_artifact")
    async def search_kb(query: str) -> tuple[str, list[str]]:
        """Search the AtlasFlow knowledge base for relevant documentation."""

        results = await knowledge_base.search(query)
        if not results:
            return "No relevant documentation found.", []

        documents = [doc for doc, _score in results]
        content = "\n\n".join(
            f"[source: {doc.metadata['source_id']}]\n{doc.text}" for doc in documents
        )
        return content, [str(doc.metadata["source_id"]) for doc in documents]

    return search_kb
