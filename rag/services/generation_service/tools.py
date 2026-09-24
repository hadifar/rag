from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.types import Command

from rag.services.retrieval_service.service import RetrievalService


def build_search_tool(ranking_service: RetrievalService) -> BaseTool:

    @tool
    async def search_kb(
        query: str, tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """Search the AtlasFlow knowledge base for relevant documentation."""
        results = await ranking_service.search(query)
        if not results:
            content = "No relevant documentation found."
            sources = []
        else:
            content = "\n\n".join(
                f"[source: {doc.metadata.get('source_id')}]\n{doc.page_content}"
                for doc, _score in results
            )
            sources = [doc.metadata.get("source_id") for doc, _score in results]

        return Command(
            update={
                "sources": sources,
                "messages": [ToolMessage(content=content, tool_call_id=tool_call_id)],
            }
        )

    return search_kb
