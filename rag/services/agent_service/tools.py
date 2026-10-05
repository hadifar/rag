from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import create_model

from rag.domain.models import RunContext, Tool


def _to_langchain_tool(tool: Tool) -> BaseTool:
    """The model reads the result's content; its references ride along as the
    ToolMessage's artifact, where the turn's references are collected from. The turn's
    RunContext is injected by LangChain, so the model never sees it as an argument.
    """
    fields: dict[str, Any] = {tool.parameter: (str, ...)}
    args_schema = create_model(f"{tool.name}_args", **fields)

    async def run(
        runtime: ToolRuntime[RunContext], **args: str
    ) -> tuple[str, list[str] | None]:
        result = await tool.run(args[tool.parameter], runtime.context)
        return result.content, result.references

    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=tool.description,
        args_schema=args_schema,
        response_format="content_and_artifact",
    )


def to_langchain_tools(tools: list[Tool]) -> list[BaseTool]:
    """Raises ValueError if two tools share a name, which LangChain would otherwise only
    trip over once the agent runs.
    """
    names = [tool.name for tool in tools]
    if duplicates := sorted({name for name in names if names.count(name) > 1}):
        raise ValueError(f"tool names must be unique: {', '.join(duplicates)}")

    return [_to_langchain_tool(tool) for tool in tools]
