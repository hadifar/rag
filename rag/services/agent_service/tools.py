from langchain_core.tools import BaseTool, StructuredTool

from rag.domain.agents import Tool


def to_langchain_tool(tool: Tool) -> BaseTool:
    """The model reads the result's content; its references ride along as the
    ToolMessage's artifact, where the turn's references are collected from.
    """

    async def run(query: str) -> tuple[str, list[str] | None]:
        result = await tool.run(query)
        return result.content, result.references

    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=tool.description,
        response_format="content_and_artifact",
    )
