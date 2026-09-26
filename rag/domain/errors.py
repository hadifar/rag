class RagError(Exception):
    """Base for every exception the domain/services layer raises deliberately."""


class DocumentNotFoundError(RagError):
    """Raised when a document lookup by source_id finds nothing."""

    def __init__(self, source_id: str):
        super().__init__(f"No document found for source_id={source_id!r}")
        self.source_id = source_id


class VectorStoreConfigurationError(RagError):
    """Raised when the configured vector store backend can't be used as configured."""


class InvalidCredentialsError(RagError):
    """Raised when a login attempt's email/password don't match a user."""

    def __init__(self):
        super().__init__("Invalid email or password")


class UserNotFoundError(RagError):
    """Raised when a user lookup by id finds nothing (e.g. deleted after token issue)."""

    def __init__(self, user_id: object):
        super().__init__(f"No user found for id={user_id!r}")
        self.user_id = user_id


class InvalidTokenError(RagError):
    """Raised when a JWT is missing, malformed, expired, or the wrong type."""

    def __init__(self, reason: str):
        super().__init__(f"Invalid token: {reason}")
