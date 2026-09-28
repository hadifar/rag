from typing import ClassVar


class RagError(Exception):
    """Base for every exception the domain/services layer raises deliberately."""

    status_code: ClassVar[int] = 500


class DocumentNotFoundError(RagError):
    """Raised when a document lookup by source_id finds nothing."""

    status_code: ClassVar[int] = 404

    def __init__(self, source_id: str):
        super().__init__(f"No document found for source_id={source_id!r}")
        self.source_id = source_id


class InvalidArchiveError(RagError):
    """Raised when a knowledge-base zip can't be read, or its contents are rejected."""

    status_code: ClassVar[int] = 400

    def __init__(self, reason: str):
        super().__init__(f"Invalid knowledge-base archive: {reason}")


class EmptyKnowledgeBaseError(RagError):
    """Raised when a source has no documents; ingesting it would empty the index."""

    status_code: ClassVar[int] = 400

    def __init__(self):
        super().__init__("The knowledge-base source contains no documents")


class NoArchiveError(RagError):
    """Raised when asked to ingest the latest uploaded archive, but none exists."""

    status_code: ClassVar[int] = 404

    def __init__(self):
        super().__init__("No knowledge-base archive has been uploaded yet")


class VectorStoreConfigurationError(RagError):
    """Raised when the configured vector store backend can't be used as configured."""


class InvalidCredentialsError(RagError):
    """Raised when a login attempt's email/password don't match a user."""

    status_code: ClassVar[int] = 401

    def __init__(self):
        super().__init__("Invalid email or password")


class UserNotFoundError(RagError):
    """Raised when a user lookup by id finds nothing (e.g. deleted after token issue)."""

    status_code: ClassVar[int] = 401

    def __init__(self, user_id: object):
        super().__init__(f"No user found for id={user_id!r}")
        self.user_id = user_id


class InvalidTokenError(RagError):
    """Raised when a JWT is missing, malformed, expired, or the wrong type."""

    status_code: ClassVar[int] = 401

    def __init__(self, reason: str):
        super().__init__(f"Invalid token: {reason}")


class ConversationNotFoundError(RagError):
    """Raised when a conversation doesn't exist or belongs to another user.

    One error for both, so a caller can't probe which ids exist.
    """

    status_code: ClassVar[int] = 404

    def __init__(self, conversation_id: object):
        super().__init__(f"No conversation found for id={conversation_id!r}")
        self.conversation_id = conversation_id


class InvalidCursorError(RagError):
    """Raised when a pagination cursor wasn't produced by this API."""

    status_code: ClassVar[int] = 400

    def __init__(self):
        super().__init__("Invalid pagination cursor")
