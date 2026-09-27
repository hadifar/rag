from collections.abc import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage


def current_turn(messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """The messages from the user's latest message onward.

    Guards inject their instructions per model call instead of saving them to the
    thread, so the last HumanMessage in state is always the user's.
    """
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index:]
    return messages


def turn_tool_messages(messages: Sequence[BaseMessage]) -> list[ToolMessage]:
    return [m for m in current_turn(messages) if isinstance(m, ToolMessage)]


def turn_sources(messages: Sequence[BaseMessage]) -> list[str]:
    """Deduplicated source ids search_kb attached (as its artifact) this turn."""
    return sorted(
        {
            source
            for message in turn_tool_messages(messages)
            if isinstance(message.artifact, list)
            for source in message.artifact
        }
    )
