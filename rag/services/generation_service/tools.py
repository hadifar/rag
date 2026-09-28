from langchain_core.tools import BaseTool, tool

from rag.services.retrieval_service.service import RetrievalService


def build_search_tool(retrieval_service: RetrievalService) -> BaseTool:

    @tool(response_format="content_and_artifact")
    async def search_kb(query: str) -> tuple[str, list[str]]:
        """Search the AtlasFlow knowledge base for relevant documentation."""

        results = await retrieval_service.search(query)
        if not results:
            return "No relevant documentation found.", []

        content = "\n\n".join(
            f"[source: {doc.metadata.get('source_id')}]\n{doc.page_content}"
            for doc, _score in results
        )

        sources = [
            doc.metadata["source_id"]
            for doc, _score in results
            if doc.metadata.get("source_id")
        ]
        return content, sources

    return search_kb
