from typing import Any

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from pydantic import TypeAdapter

from rag.domain.errors import (
    InvalidPreferenceError,
    PreferenceNotFoundError,
    TooManyPreferencesError,
)
from rag.domain.models import Artifact, RunContext, SourceArtifact
from rag.domain.ports import PreferencesPort, SearchPort
from rag.services.agent_service.prompts import (
    FORGET_TOOL_DESCRIPTION,
    SAVE_TOOL_DESCRIPTION,
)

_ARTIFACTS = TypeAdapter(list[Artifact])

SAVE_PREFERENCE = "save_user_preference"
FORGET_PREFERENCE = "forget_user_preference"

# Tools that act on the user, not the product: the off-topic guard keeps them, and
# their results aren't what an answer is checked against.
USER_TOOLS = frozenset({SAVE_PREFERENCE, FORGET_PREFERENCE})


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
        return content, _ARTIFACTS.dump_python(sources, mode="json")

    return search_kb


def preference_tools(preferences: PreferencesPort) -> list[BaseTool]:
    """Save and forget the user's preferences. The user is the turn's (its RunContext,
    which LangChain injects), never one the model names; a rejected change is reported
    to the model, not raised.
    """

    @tool(SAVE_PREFERENCE, description=SAVE_TOOL_DESCRIPTION)
    async def save(text: str, runtime: ToolRuntime[RunContext]) -> str:
        try:
            preference = await preferences.add(runtime.context.user_id, text)
        except (InvalidPreferenceError, TooManyPreferencesError) as exc:
            return f"Not saved: {exc}"
        return f"Saved preference {preference.id}: {preference.text}"

    @tool(FORGET_PREFERENCE, description=FORGET_TOOL_DESCRIPTION)
    async def forget(preference_id: str, runtime: ToolRuntime[RunContext]) -> str:
        try:
            await preferences.delete(runtime.context.user_id, preference_id)
        except PreferenceNotFoundError:
            return f"No saved preference has the id {preference_id}."
        return f"Forgot preference {preference_id}."

    return [save, forget]
