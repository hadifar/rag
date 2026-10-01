from typing import ClassVar


class AppError(Exception):
    status_code: ClassVar[int] = 500


class DocumentNotFoundError(AppError):
    """Raised when a document lookup by source_id finds nothing."""

    status_code: ClassVar[int] = 404

    def __init__(self, source_id: str):
        super().__init__(f"No document found for source_id={source_id!r}")
        self.source_id = source_id


class InvalidArchiveError(AppError):
    """Raised when a knowledge-base zip can't be read, or its contents are rejected."""

    status_code: ClassVar[int] = 400

    def __init__(self, reason: str):
        super().__init__(f"Invalid knowledge-base archive: {reason}")


class EmptyKnowledgeBaseError(AppError):
    """Raised when a source has no documents; ingesting it would empty the index."""

    status_code: ClassVar[int] = 400

    def __init__(self):
        super().__init__("The knowledge-base source contains no documents")


class ArchiveTooLargeError(AppError):
    """Raised when an uploaded knowledge-base zip is over the size limit."""

    status_code: ClassVar[int] = 413

    def __init__(self, max_bytes: int):
        super().__init__(f"The archive is larger than {max_bytes // (1024 * 1024)} MB")


class IngestionInProgressError(AppError):
    """Raised when an ingestion is started while another one is still running."""

    status_code: ClassVar[int] = 409

    def __init__(self):
        super().__init__("Another ingestion is still running; try again when it ends")


class IngestionRunNotFoundError(AppError):
    status_code: ClassVar[int] = 404

    def __init__(self, run_id: object):
        super().__init__(f"No ingestion run found for id={run_id!r}")


class NoArchiveError(AppError):
    """Raised when asked to ingest the latest uploaded archive, but none exists."""

    status_code: ClassVar[int] = 404

    def __init__(self):
        super().__init__("No knowledge-base archive has been uploaded yet")


class InvalidCredentialsError(AppError):
    """Raised when a login attempt's email/password don't match a user."""

    status_code: ClassVar[int] = 401

    def __init__(self):
        super().__init__("Invalid email or password")


class UserNotFoundError(AppError):
    """Raised when a user lookup by id finds nothing (e.g. deleted after token issue)."""

    status_code: ClassVar[int] = 401

    def __init__(self, user_id: object):
        super().__init__(f"No user found for id={user_id!r}")
        self.user_id = user_id


class UserEmailNotFoundError(AppError):
    """Raised when a user lookup by email finds nothing (e.g. granting admin rights)."""

    status_code: ClassVar[int] = 404

    def __init__(self, email: str):
        super().__init__(f"No user found for email={email!r}")


class UserAlreadyExistsError(AppError):
    """Raised when creating a user with an email another user already has."""

    status_code: ClassVar[int] = 409

    def __init__(self, email: str):
        super().__init__(f"A user with email={email!r} already exists")


class InvalidTokenError(AppError):
    """Raised when a JWT is missing, malformed, expired, or the wrong type."""

    status_code: ClassVar[int] = 401

    def __init__(self, reason: str):
        super().__init__(f"Invalid token: {reason}")


class AdminRequiredError(AppError):
    """Raised when a signed-in user who isn't an admin calls an admin-only endpoint."""

    status_code: ClassVar[int] = 403

    def __init__(self):
        super().__init__("Admin access required")


class ConversationNotFoundError(AppError):
    """Raised when a conversation doesn't exist or belongs to another user.

    One error for both, so a caller can't probe which ids exist.
    """

    status_code: ClassVar[int] = 404

    def __init__(self, conversation_id: object):
        super().__init__(f"No conversation found for id={conversation_id!r}")
        self.conversation_id = conversation_id


class InvalidCursorError(AppError):
    """Raised when a pagination cursor wasn't produced by this API."""

    status_code: ClassVar[int] = 400

    def __init__(self):
        super().__init__("Invalid pagination cursor")


class BlankTitleError(AppError):
    """Raised when the LLM's conversation title is blank."""

    status_code: ClassVar[int] = 502

    def __init__(self):
        super().__init__("The LLM returned a blank conversation title")


class InvalidPreferenceError(AppError):
    """Raised when a preference is blank or too long."""

    status_code: ClassVar[int] = 400

    def __init__(self, reason: str):
        super().__init__(f"Invalid preference: {reason}")


class TooManyPreferencesError(AppError):
    """Raised when a user who already has the most preferences allowed adds another."""

    status_code: ClassVar[int] = 409

    def __init__(self, max_preferences: int):
        super().__init__(
            f"You can keep at most {max_preferences} preferences; remove one first"
        )
