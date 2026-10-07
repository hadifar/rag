from typing import ClassVar


class AppError(Exception):
    status_code: ClassVar[int] = 500


class DocumentNotFoundError(AppError):
    """Raised when a document lookup by source_id finds nothing."""

    status_code: ClassVar[int] = 404

    def __init__(self, source_id: str):
        super().__init__(f"No document found for source_id={source_id!r}")


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


class NothingToShareError(AppError):
    """Raised when sharing a conversation that has no messages yet."""

    status_code: ClassVar[int] = 409

    def __init__(self, conversation_id: object):
        super().__init__(f"Conversation {conversation_id!r} has no messages to share")


class ShareNotFoundError(AppError):
    """Raised when a share link doesn't exist, was taken down, or its conversation
    was deleted.
    """

    status_code: ClassVar[int] = 404

    def __init__(self, share_id: object):
        super().__init__(f"No shared conversation found for id={share_id!r}")


class InvalidCursorError(AppError):
    """Raised when a pagination cursor wasn't produced by this API."""

    status_code: ClassVar[int] = 400

    def __init__(self):
        super().__init__("Invalid pagination cursor")


class AttachmentNotFoundError(AppError):
    """Raised when an attachment doesn't exist, isn't in the conversation, or (to
    discard it) was already sent.
    """

    status_code: ClassVar[int] = 404

    def __init__(self, attachment_id: object):
        super().__init__(f"No attachment found for id={attachment_id!r}")


class UnsupportedAttachmentError(AppError):
    """Raised when an uploaded file isn't one of the kinds that can be attached."""

    status_code: ClassVar[int] = 415

    def __init__(self, accepted: str):
        super().__init__(f"Only {accepted} files can be attached")


class AttachmentTooLargeError(AppError):
    """Raised when an uploaded file is over its kind's size limit."""

    status_code: ClassVar[int] = 413

    def __init__(self, max_bytes: int):
        super().__init__(f"The file is larger than {_size(max_bytes)}")


class SkillNotFoundError(AppError):
    """Raised when a skill doesn't exist or belongs to another user."""

    status_code: ClassVar[int] = 404

    def __init__(self, skill_id: object):
        super().__init__(f"No skill found for id={skill_id!r}")


class InvalidSkillError(AppError):
    """Raised when an uploaded skill file can't be read as a skill."""

    status_code: ClassVar[int] = 422

    def __init__(self, reason: str):
        super().__init__(f"Not a valid skill file: {reason}")


class SkillTooLargeError(AppError):
    """Raised when an uploaded skill file is over the size limit."""

    status_code: ClassVar[int] = 413

    def __init__(self, max_bytes: int):
        super().__init__(f"The skill file is larger than {_size(max_bytes)}")


class TooManySkillsError(AppError):
    """Raised when saving a new skill would take a user over the limit."""

    status_code: ClassVar[int] = 409

    def __init__(self, max_skills: int):
        super().__init__(
            f"You can save up to {max_skills} skills. Delete one to add another."
        )


def _size(n: int) -> str:
    return f"{n // (1024 * 1024)} MB" if n >= 1024 * 1024 else f"{n // 1024} KB"
