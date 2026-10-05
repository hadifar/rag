from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import TypeAdapter, create_model

from rag.domain.models import Artifact, RunContext, Tool

_ARTIFACTS = TypeAdapter(list[Artifact])


def _to_langchain_tool(tool: Tool) -> BaseTool:
    """The model reads the result's content; its artifacts ride along as the
    ToolMessage's artifact, where the turn's artifacts are collected from. They're kept
    there as plain JSON, which the checkpointer saves as is, rather than as domain
    classes it would have to be told it may load. The turn's RunContext is injected by
    LangChain, so the model never sees it as an argument.
    """
    fields: dict[str, Any] = {tool.parameter: (str, ...)}
    args_schema = create_model(f"{tool.name}_args", **fields)

    async def run(
        runtime: ToolRuntime[RunContext], **args: str
    ) -> tuple[str, list[dict[str, Any]] | None]:
        result = await tool.run(args[tool.parameter], runtime.context)
        if result.artifacts is None:
            return result.content, None
        return result.content, _ARTIFACTS.dump_python(result.artifacts, mode="json")

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
