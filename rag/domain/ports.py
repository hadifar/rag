import uuid
from collections.abc import AsyncIterator, Callable, Mapping
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel

from rag.domain.models import (
    Chunk,
    Conversation,
    HistoryMessage,
    IndexedDocument,
    IngestionReport,
    IngestionRun,
    RawDocument,
    User,
)


class EmbeddingsPort(Protocol):
    async def aembed_query(self, text: str) -> list[float]: ...
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...


class VectorStorePort(Protocol):
    async def asimilarity_search_with_score(
        self, query: str, k: int
    ) -> list[tuple[Chunk, float]]: ...
    async def aget_document(self, source_id: str) -> Chunk | None: ...
    async def aping(self) -> None:
        """Raises if the store can't serve queries; must be cheap (readiness probe)."""
        ...


class SearchPort(Protocol):
    """Finds knowledge-base passages for a query: the best first, with their scores."""

    async def search(self, query: str) -> list[tuple[Chunk, float]]: ...


class DocumentIndexPort(Protocol):
    """The write side of the knowledge base: what's indexed, and replacing it."""

    async def alist_content_hashes(self) -> dict[str, str]:
        """source_id -> content hash, for every indexed document."""
        ...

    async def areplace_documents(
        self, documents: list[IndexedDocument], *, removed: list[str]
    ) -> None:
        """Re-indexes `documents` (embedding their chunks) and drops `removed`, all in
        one transaction.
        """
        ...


class ArchiveStorePort(Protocol):
    """Keeps every uploaded knowledge-base zip, so the index can always be rebuilt."""

    async def asave(self, data: bytes) -> str:
        """Stores `data` under a new name and returns it. Names sort by upload time."""
        ...

    async def aread(self, name: str) -> bytes: ...
    async def alatest(self) -> str | None:
        """The most recently saved archive's name, or None if there are none."""
        ...


class IngestionRunRepositoryPort(Protocol):
    async def create(
        self, archive_name: str, created_by: uuid.UUID | None
    ) -> IngestionRun:
        """Starts a run as `running`; raises IngestionInProgressError if one already is."""
        ...

    async def get(self, run_id: uuid.UUID) -> IngestionRun | None: ...
    async def latest(self) -> IngestionRun | None: ...
    async def running(self) -> IngestionRun | None: ...
    async def finish(self, run_id: uuid.UUID, report: IngestionReport) -> None: ...
    async def fail(self, run_id: uuid.UUID, error: str) -> None: ...
    async def fail_running(self, error: str) -> int:
        """Marks every still-running run failed; returns how many there were."""
        ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Chunk]: ...


class UserRepositoryPort(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def create(
        self, email: str, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        """Raises UserAlreadyExistsError if the email is taken."""
        ...

    async def set_admin(self, email: str, is_admin: bool) -> User | None:
        """None if no user has that email."""
        ...


class ConversationRepositoryPort(Protocol):
    async def get_or_create_empty(self, user_id: uuid.UUID) -> Conversation:
        """The user's empty (untitled) conversation, created if they have none, and
        bumped to most recently used. A user has at most one.
        """
        ...

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None,
    ) -> list[Conversation]:
        """Newest first by (updated_at, id); `before` is exclusive (keyset pagination)."""
        ...

    async def touch(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def set_title(self, conversation_id: uuid.UUID, title: str) -> None: ...
    async def delete(self, conversation_id: uuid.UUID) -> None: ...
    async def all_ids(self) -> set[uuid.UUID]:
        """Every conversation's id, whoever owns it."""
        ...

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        """The thread's messages as the user saw them; empty for an unknown thread."""
        ...

    async def delete_history(self, thread_id: str) -> None: ...
    async def list_thread_ids(self) -> set[str]:
        """Every thread that has stored messages."""
        ...


class HistoryStorePort(Protocol):
    """The chat messages stored per thread, which the chat agent writes as it answers."""

    async def get_history(self, thread_id: str) -> list[HistoryMessage]:
        """The thread's messages as the user saw them; empty for an unknown thread."""
        ...

    async def delete_history(self, thread_id: str) -> None: ...
    async def list_thread_ids(self) -> set[str]:
        """Every thread that has stored messages."""
        ...


class GenerationPort(Protocol):
    """The LLM: plain text generation, and building and streaming agents on it, so
    nothing else ever holds the model. Tools, middleware, graph and config are typed
    loosely: the domain stays free of LangChain.
    """

    async def generate(self, prompt: str, *, attempts: int = 1) -> str:
        """One-shot completion as plain text, tried up to `attempts` times; raises if
        all fail. To bound the time, wrap the call in `asyncio.timeout`.
        """
        ...

    async def generate_structured[T: BaseModel](
        self, prompt: str, schema: type[T], *, attempts: int = 1
    ) -> T:
        """One-shot completion enforced to fit `schema` (a Pydantic model class), as an
        instance of it; raises if all `attempts` fail or the reply is rejected.
        """
        ...

    def stream(self, prompt: str) -> AsyncIterator[str]:
        """The completion's text, token by token."""
        ...

    def create_agent(
        self,
        tools: list[Any],
        system_prompt: str,
        middleware: list[Any],
        checkpointer: Any,
    ) -> Any:
        """A tool-calling agent graph on the model, saving its threads to `checkpointer`."""
        ...

    def stream_events[E](
        self,
        graph: Any,
        messages: list[Any],
        config: Any,
        parse: Callable[[Mapping[str, Any]], E | None],
    ) -> AsyncIterator[E]:
        """Runs `graph` and yields what `parse` makes of each raw event (None skips)."""
        ...
