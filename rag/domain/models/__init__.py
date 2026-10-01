"""The domain's data types, grouped by area; import them from here."""

from rag.domain.models.agent.agent import (
    MAX_PREFERENCE_LENGTH,
    MAX_PREFERENCES,
    AgentSpec,
    Middleware,
    Preference,
    Tool,
    ToolAgentSpec,
    ToolResult,
)
from rag.domain.models.agent.middleware import (
    GroundednessMiddleware,
    OffTopicMiddleware,
    PlanningMiddleware,
    PreferenceMiddleware,
)
from rag.domain.models.agent.stream import (
    ReferencesReady,
    StreamEvent,
    TextDelta,
    ToolCall,
)
from rag.domain.models.auth import User
from rag.domain.models.conversation import (
    Conversation,
    ConversationPage,
    HistoryMessage,
)
from rag.domain.models.ingestion import (
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    IngestionRunStatus,
    RawDocument,
)
from rag.domain.models.retrieval import Chunk

__all__ = [
    "MAX_PREFERENCES",
    "MAX_PREFERENCE_LENGTH",
    "AgentSpec",
    "Chunk",
    "Conversation",
    "ConversationPage",
    "GroundednessMiddleware",
    "HistoryMessage",
    "IndexedDocument",
    "IngestionReport",
    "IngestionRun",
    "IngestionRunStatus",
    "Middleware",
    "OffTopicMiddleware",
    "PlanningMiddleware",
    "Preference",
    "PreferenceMiddleware",
    "RawDocument",
    "ReferencesReady",
    "StreamEvent",
    "TextDelta",
    "Tool",
    "ToolAgentSpec",
    "ToolCall",
    "ToolResult",
    "User",
]
