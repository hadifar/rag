from langchain_core.tools import BaseTool, tool

from rag.services.ranking_service.service import RankingService


def build_search_tool(ranking_service: RankingService) -> BaseTool:
    """Closure over an injected RankingService — see engineering_design.md's note on
    reconciling LangGraph's module-level @tool convention with constructor injection.
    """

    @tool
    async def search_kb(query: str) -> str:
        """Search the AtlasFlow knowledge base for relevant documentation."""
        results = await ranking_service.search(query)
        if not results:
            return "No relevant documentation found."
        return "\n\n".join(
            f"[source: {doc.metadata.get('source_id')}]\n{doc.page_content}"
            for doc, _score in results
        )

    return search_kb
