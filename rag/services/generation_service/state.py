from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    relevant: NotRequired[bool]
    grounded: NotRequired[bool]
    verify_attempts: NotRequired[int]
