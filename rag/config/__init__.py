"""The app's settings, read from the environment and .env; import them from here.

Each module is one section of `Settings`, named after its env prefix: `KB_STORAGE__DIR`
lives in kb_storage.py. A section's model is `<Section>Config` (the union of its
backends, where it has several), and each backend is `<Backend><Section>Config`.
Unprefixed fields (DATABASE_URL, HOST, ...) sit on `Settings` itself, in settings.py.
"""

from rag.config.auth import AuthConfig
from rag.config.kb_storage import (
    AzureBlobKbStorageConfig,
    KbStorageConfig,
    LocalKbStorageConfig,
)
from rag.config.llm import AzureOpenAILLMConfig, LLMConfig, OpenAILLMConfig
from rag.config.observability import (
    LangfuseObservabilityConfig,
    LoggingObservabilityConfig,
    ObservabilityConfig,
)
from rag.config.rag import RagConfig
from rag.config.settings import Settings, get_settings

__all__ = [
    "AuthConfig",
    "AzureBlobKbStorageConfig",
    "AzureOpenAILLMConfig",
    "KbStorageConfig",
    "LLMConfig",
    "LangfuseObservabilityConfig",
    "LocalKbStorageConfig",
    "LoggingObservabilityConfig",
    "ObservabilityConfig",
    "OpenAILLMConfig",
    "RagConfig",
    "Settings",
    "get_settings",
]
